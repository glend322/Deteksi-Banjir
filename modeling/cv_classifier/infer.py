"""
CV Flood Image Classifier - Inference

Usage:
  python infer.py --image path/to/image.jpg
  python infer.py --image path/to/image.jpg --checkpoint checkpoints/best.pt
  python infer.py --dir path/to/images/
"""
import argparse
import json
import sys
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).parent))
from model import FloodClassifier, SEVERITY_CLASSES, DEPTH_BUCKETS, DEPTH_BUCKET_LABELS, depth_to_bucket

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"

RISK_THRESHOLDS = {"normal": 0.2, "waspada": 0.5, "tergenang": 0.8}


def load_model(checkpoint: str | None, device: torch.device) -> FloodClassifier:
    path = Path(checkpoint) if checkpoint else CHECKPOINT_DIR / "best.pt"
    ckpt = torch.load(path, map_location=device, weights_only=False)
    backbone = ckpt.get("backbone", "resnet50")
    model = FloodClassifier(num_classes=4, pretrained=False, backbone=backbone)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    return model


def build_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


@torch.no_grad()
def predict_image(model, img_path: str, device: torch.device) -> dict:
    img = Image.open(img_path).convert("RGB")
    transform = build_transform()
    tensor = transform(img).unsqueeze(0).to(device)

    out = model(tensor)
    probs = torch.softmax(out["logits"], dim=1).cpu().numpy()[0]
    depth_cm = float(out["depth_cm"].cpu().numpy()[0])
    depth_cm = max(0.0, min(depth_cm, 200.0))

    pred_class = int(probs.argmax())
    confidence = float(probs[pred_class])

    # Flood probability = sum of non-normal classes
    flood_prob = float(sum(probs[1:]))

    if flood_prob > RISK_THRESHOLDS["tergenang"]:
        risk_level = "tidak_dapat_dilalui"
    elif flood_prob > RISK_THRESHOLDS["waspada"]:
        risk_level = "tergenang"
    elif flood_prob > RISK_THRESHOLDS["normal"]:
        risk_level = "waspada"
    else:
        risk_level = "normal"

    return {
        "image": str(img_path),
        "flood_detected": pred_class > 0,
        "severity_class": SEVERITY_CLASSES[pred_class],
        "severity_label": SEVERITY_CLASSES[pred_class],
        "risk_level": risk_level,
        "flood_probability": round(flood_prob, 4),
        "confidence": round(confidence, 4),
        "depth_estimate_cm": round(depth_cm, 1),
        "depth_range": depth_to_bucket(depth_cm),
        "probabilities": {c: round(float(probs[i]), 4) for i, c in enumerate(SEVERITY_CLASSES)},
    }


def main():
    parser = argparse.ArgumentParser(description="Flood image inference")
    parser.add_argument("--image", type=str, help="Single image path")
    parser.add_argument("--dir", type=str, help="Directory of images")
    parser.add_argument("--checkpoint", type=str, default=None, help="Model checkpoint path")
    parser.add_argument("--output", type=str, default=None, help="Output JSON path")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = load_model(args.checkpoint, device)

    results = []

    if args.image:
        result = predict_image(model, args.image, device)
        results.append(result)

    elif args.dir:
        img_dir = Path(args.dir)
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() in exts:
                result = predict_image(model, str(img_path), device)
                results.append(result)

    else:
        parser.error("Provide --image or --dir")

    output_json = json.dumps(results, indent=2, default=str)
    if args.output:
        Path(args.output).write_text(output_json)
        print(f"Saved {len(results)} predictions to {args.output}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
