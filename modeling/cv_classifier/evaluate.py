"""
CV Flood Image Classifier - Evaluation

Computes on test set:
- Classification: accuracy, F1, precision, recall, AUC-ROC, confusion matrix
- Regression: MAE, RMSE, R² for depth estimation
- Per-class analysis
"""
import json
import sys
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    f1_score,
    accuracy_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)

sys.path.insert(0, str(Path(__file__).parent))
from model import FloodClassifier, SEVERITY_CLASSES
from dataset import prepare_dataloaders

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


def load_model(device: torch.device, checkpoint: str | None = None) -> FloodClassifier:
    path = Path(checkpoint) if checkpoint else CHECKPOINT_DIR / "best.pt"
    ckpt = torch.load(path, map_location=device, weights_only=False)
    backbone = ckpt.get("backbone", "resnet50")
    model = FloodClassifier(num_classes=4, pretrained=False, backbone=backbone)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()
    return model


@torch.no_grad()
def evaluate():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    model = load_model(device)
    loaders = prepare_dataloaders(image_size=224, batch_size=32, augment=False)
    loader = loaders["test"]

    all_preds = []
    all_labels = []
    all_probs = []
    all_depths_true = []
    all_depths_pred = []

    for imgs, targets in loader:
        imgs = imgs.to(device)
        out = model(imgs)

        probs = torch.softmax(out["logits"], dim=1).cpu().numpy()
        preds = out["logits"].argmax(dim=1).cpu().numpy()
        depths = out["depth_cm"].cpu().numpy()

        all_preds.extend(preds)
        all_labels.extend(targets["label"].numpy())
        all_probs.extend(probs)
        all_depths_true.extend(targets["depth_cm"].numpy())
        all_depths_pred.extend(depths)

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs = np.array(all_probs)
    all_depths_true = np.array(all_depths_true)
    all_depths_pred = np.array(all_depths_pred)

    # === Classification ===
    print("\n" + "=" * 60)
    print("CLASSIFICATION METRICS (Flood Severity)")
    print("=" * 60)

    accuracy = accuracy_score(all_labels, all_preds)
    f1_weighted = f1_score(all_labels, all_preds, average="weighted", zero_division=0)
    f1_macro = f1_score(all_labels, all_preds, average="macro", zero_division=0)

    print(f"\nAccuracy:  {accuracy:.4f}")
    print(f"F1 (weighted): {f1_weighted:.4f}")
    print(f"F1 (macro):    {f1_macro:.4f}")

    # AUC-ROC
    try:
        auc = roc_auc_score(all_labels, all_probs, multi_class="ovr", average="weighted")
        print(f"AUC-ROC (weighted): {auc:.4f}")
    except ValueError:
        auc = 0.0
        print("AUC-ROC: N/A")

    # Per-class report
    present = np.unique(np.concatenate([all_labels, all_preds]))
    names = [SEVERITY_CLASSES[i] for i in present if i < len(SEVERITY_CLASSES)]
    print(f"\nClassification Report:")
    print(classification_report(all_labels, all_preds, target_names=names, zero_division=0))

    # Confusion matrix
    print("Confusion Matrix:")
    cm = confusion_matrix(all_labels, all_preds)
    print(cm)

    # === Regression (Depth) ===
    print("\n" + "=" * 60)
    print("REGRESSION METRICS (Water Depth)")
    print("=" * 60)

    mae = mean_absolute_error(all_depths_true, all_depths_pred)
    rmse = np.sqrt(mean_squared_error(all_depths_true, all_depths_pred))
    r2 = r2_score(all_depths_true, all_depths_pred)

    print(f"\nMAE:  {mae:.2f} cm")
    print(f"RMSE: {rmse:.2f} cm")
    print(f"R²:   {r2:.4f}")

    # Depth bucket accuracy
    def depth_bucket(d):
        if d < 20:
            return "<20cm"
        elif d < 40:
            return "20-40cm"
        elif d < 70:
            return "40-70cm"
        else:
            return ">70cm"

    actual_buckets = [depth_bucket(d) for d in all_depths_true]
    pred_buckets = [depth_bucket(d) for d in all_depths_pred]
    bucket_acc = sum(a == p for a, p in zip(actual_buckets, pred_buckets)) / len(actual_buckets)
    print(f"Depth Bucket Accuracy: {bucket_acc:.4f}")

    # === Summary ===
    results = {
        "test_size": len(all_labels),
        "classification": {
            "accuracy": round(float(accuracy), 4),
            "f1_weighted": round(float(f1_weighted), 4),
            "f1_macro": round(float(f1_macro), 4),
            "auc_roc": round(float(auc), 4),
        },
        "regression": {
            "mae_cm": round(float(mae), 2),
            "rmse_cm": round(float(rmse), 2),
            "r2": round(float(r2), 4),
            "depth_bucket_accuracy": round(float(bucket_acc), 4),
        },
        "confusion_matrix": cm.tolist(),
    }

    out_path = CHECKPOINT_DIR / "evaluation_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved: {out_path}")

    return results


if __name__ == "__main__":
    evaluate()
