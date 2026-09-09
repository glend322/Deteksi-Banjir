"""
Model Inference Test — Run model on real images from training data.
Tests flood detection, depth classification, and cause detection accuracy.
"""
import sys
sys.path.insert(0, ".")

import os
import json
import random
import time
import torch
import numpy as np
from pathlib import Path
from PIL import Image
from torchvision import transforms
from detection.cv_model import (
    FloodClassifier, CLASS_NAMES, CAUSE_NAMES, DEPTH_BUCKET_LABELS,
    depth_to_classification, cause_to_text
)

DATA_DIR = Path("data/training")
CHECKPOINT_PATH = Path("checkpoints/best.pt")
NUM_SAMPLES = 30  # images per class to test

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model():
    ckpt = torch.load(CHECKPOINT_PATH, map_location=DEVICE, weights_only=False)
    backbone = ckpt.get("backbone", "resnet50")
    model = FloodClassifier(num_classes=2, num_causes=2, pretrained=False, backbone=backbone)
    model.load_state_dict(ckpt["model_state_dict"], strict=False)
    model.to(DEVICE)
    model.eval()
    print(f"Model loaded: backbone={backbone}, device={DEVICE}")
    print(f"Checkpoint epoch: {ckpt.get('epoch', '?')}, val_acc: {ckpt.get('val_acc', '?')}")
    return model


def get_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def sample_images(directory, n):
    images = list(Path(directory).glob("*.jpg")) + list(Path(directory).glob("*.png"))
    if len(images) == 0:
        return []
    return random.sample(images, min(n, len(images)))


def run_inference(model, img_path, transform):
    img = Image.open(img_path).convert("RGB")
    tensor = transform(img).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        out = model(tensor)

    flood_probs = torch.softmax(out["logits"], dim=1).cpu().numpy()[0]
    cause_probs = torch.sigmoid(out["cause_logits"]).cpu().numpy()[0]
    depth_probs = torch.softmax(out["depth_logits"], dim=1).cpu().numpy()[0]
    depth_value = float(out["depth_value"].cpu().numpy().flatten()[0])

    flood_class = int(flood_probs.argmax())
    confidence = float(flood_probs[flood_class])
    depth_class = int(depth_probs.argmax())
    depth_label = DEPTH_BUCKET_LABELS[depth_class]

    cause_dict = {name: float(prob) for name, prob in zip(CAUSE_NAMES, cause_probs)}
    cause_text = cause_to_text(cause_dict, threshold=0.5)

    return {
        "flood_detected": flood_class == 1 or float(flood_probs[1]) > 0.5,
        "flood_class": CLASS_NAMES[flood_class],
        "flood_prob": float(flood_probs[1]) if len(flood_probs) > 1 else float(flood_probs[0]),
        "confidence": confidence,
        "depth_label": depth_label,
        "depth_class": depth_class,
        "depth_value_cm": depth_value,
        "cause_dict": cause_dict,
        "cause_text": cause_text,
    }


def test_flood_detection(model, transform):
    """Test flood vs nonflood classification."""
    print("\n=== Test 1: Flood Detection Accuracy ===")

    flood_imgs = sample_images(DATA_DIR / "flood", NUM_SAMPLES)
    nonflood_imgs = sample_images(DATA_DIR / "nonflood", NUM_SAMPLES)

    tp = fp = tn = fn = 0
    flood_confidences = []
    nonflood_confidences = []

    for img_path in flood_imgs:
        result = run_inference(model, img_path, transform)
        is_correct = result["flood_detected"]
        if is_correct:
            tp += 1
        else:
            fn += 1
        flood_confidences.append(result["flood_prob"])

    for img_path in nonflood_imgs:
        result = run_inference(model, img_path, transform)
        is_correct = not result["flood_detected"]
        if is_correct:
            tn += 1
        else:
            fp += 1
        nonflood_confidences.append(result["flood_prob"])

    total = tp + tn + fp + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    avg_flood_conf = np.mean(flood_confidences) if flood_confidences else 0
    avg_nonflood_conf = np.mean(nonflood_confidences) if nonflood_confidences else 0

    print(f"  Flood images tested:     {len(flood_imgs)}")
    print(f"  Nonflood images tested:  {len(nonflood_imgs)}")
    print(f"  TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"  Accuracy:  {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"  Precision: {precision:.4f}")
    print(f"  Recall:    {recall:.4f}")
    print(f"  F1 Score:  {f1:.4f}")
    print(f"  Avg flood prob (flood imgs):     {avg_flood_conf:.4f}")
    print(f"  Avg flood prob (nonflood imgs):  {avg_nonflood_conf:.4f}")

    return accuracy, f1


def test_cause_detection(model, transform):
    """Test cause detection (river vs trash)."""
    print("\n=== Test 2: Cause Detection Accuracy ===")

    river_imgs = sample_images(DATA_DIR / "flood_river", NUM_SAMPLES)
    trash_imgs = sample_images(DATA_DIR / "flood_trash", NUM_SAMPLES)

    river_correct = 0
    trash_correct = 0
    river_scores = []
    trash_scores = []

    for img_path in river_imgs:
        result = run_inference(model, img_path, transform)
        is_river = result["cause_dict"].get("river", 0) > 0.5
        if is_river:
            river_correct += 1
        river_scores.append(result["cause_dict"].get("river", 0))

    for img_path in trash_imgs:
        result = run_inference(model, img_path, transform)
        is_trash = result["cause_dict"].get("trash", 0) > 0.5
        if is_trash:
            trash_correct += 1
        trash_scores.append(result["cause_dict"].get("trash", 0))

    river_acc = river_correct / len(river_imgs) if river_imgs else 0
    trash_acc = trash_correct / len(trash_imgs) if trash_imgs else 0
    overall = (river_correct + trash_correct) / (len(river_imgs) + len(trash_imgs)) if (river_imgs or trash_imgs) else 0

    print(f"  River images tested: {len(river_imgs)}")
    print(f"  Trash images tested: {len(trash_imgs)}")
    print(f"  River accuracy: {river_acc:.4f} ({river_acc*100:.1f}%)")
    print(f"  Trash accuracy: {trash_acc:.4f} ({trash_acc*100:.1f}%)")
    print(f"  Overall cause accuracy: {overall:.4f} ({overall*100:.1f}%)")
    print(f"  Avg river prob on river imgs: {np.mean(river_scores):.4f}")
    print(f"  Avg trash prob on trash imgs: {np.mean(trash_scores):.4f}")

    return overall


def test_depth_classification(model, transform):
    """Test depth bucket classification on flood images."""
    print("\n=== Test 3: Depth Classification Consistency ===")

    flood_imgs = sample_images(DATA_DIR / "flood", NUM_SAMPLES)
    bucket_counts = {"dangkal": 0, "sedang": 0, "dalam": 0}
    depth_values = []

    for img_path in flood_imgs:
        result = run_inference(model, img_path, transform)
        bucket_counts[result["depth_label"]] += 1
        depth_values.append(result["depth_value_cm"])

    print(f"  Flood images tested: {len(flood_imgs)}")
    print(f"  Depth distribution:")
    for label, count in bucket_counts.items():
        pct = count / len(flood_imgs) * 100 if flood_imgs else 0
        print(f"    {label}: {count} ({pct:.1f}%)")
    print(f"  Avg depth value: {np.mean(depth_values):.2f} cm")
    print(f"  Min depth: {np.min(depth_values):.2f} cm")
    print(f"  Max depth: {np.max(depth_values):.2f} cm")

    return bucket_counts


def test_inference_speed(model, transform):
    """Benchmark inference speed."""
    print("\n=== Test 4: Inference Speed Benchmark ===")

    flood_imgs = sample_images(DATA_DIR / "flood", 50)

    # Warmup
    for img_path in flood_imgs[:5]:
        run_inference(model, img_path, transform)

    # Benchmark
    times = []
    for img_path in flood_imgs:
        start = time.perf_counter()
        run_inference(model, img_path, transform)
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    avg_ms = np.mean(times) * 1000
    p50_ms = np.percentile(times, 50) * 1000
    p95_ms = np.percentile(times, 95) * 1000
    max_ms = np.max(times) * 1000

    print(f"  Images tested: {len(flood_imgs)}")
    print(f"  Avg inference:  {avg_ms:.1f} ms")
    print(f"  P50 latency:   {p50_ms:.1f} ms")
    print(f"  P95 latency:   {p95_ms:.1f} ms")
    print(f"  Max latency:   {max_ms:.1f} ms")
    print(f"  Throughput:     {1000/avg_ms:.1f} inferences/sec")


def test_sample_outputs(model, transform):
    """Show sample outputs from different categories."""
    print("\n=== Test 5: Sample Outputs ===")

    categories = [
        ("flood", DATA_DIR / "flood"),
        ("nonflood", DATA_DIR / "nonflood"),
        ("flood_river", DATA_DIR / "flood_river"),
        ("flood_trash", DATA_DIR / "flood_trash"),
    ]

    for cat_name, cat_dir in categories:
        imgs = sample_images(cat_dir, 2)
        for img_path in imgs:
            result = run_inference(model, img_path, transform)
            cause = result["cause_text"]
            print(f"  [{cat_name}] {img_path.name}")
            print(f"    flood={result['flood_detected']} conf={result['confidence']:.3f} "
                  f"depth={result['depth_label']}({result['depth_value_cm']:.1f}cm) cause={cause}")


if __name__ == "__main__":
    random.seed(42)
    np.random.seed(42)

    model = load_model()
    transform = get_transform()

    test_sample_outputs(model, transform)
    accuracy, f1 = test_flood_detection(model, transform)
    cause_acc = test_cause_detection(model, transform)
    test_depth_classification(model, transform)
    test_inference_speed(model, transform)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Flood detection accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
    print(f"  Flood detection F1:       {f1:.4f}")
    print(f"  Cause detection accuracy: {cause_acc:.4f} ({cause_acc*100:.1f}%)")
    print(f"  Target: flood >85%, cause >75%")
    print(f"  {'PASS' if accuracy >= 0.85 else 'FAIL'}: Flood detection target")
    print(f"  {'PASS' if cause_acc >= 0.75 else 'FAIL'}: Cause detection target")
