"""
Evaluate the predictive flood model on the test set.

Produces:
- Classification metrics (accuracy, F1, precision, recall, AUC-ROC)
- Regression metrics (MAE, RMSE, R²)
- Confusion matrix
- Per-class analysis
"""
import sys
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    f1_score,
    accuracy_score,
)

sys.path.insert(0, str(Path(__file__).parent))
from dataset import prepare_splits

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"


def load_models():
    with open(CHECKPOINT_DIR / "classifier.pkl", "rb") as f:
        clf = pickle.load(f)
    with open(CHECKPOINT_DIR / "regressor.pkl", "rb") as f:
        reg = pickle.load(f)
    return clf, reg


def evaluate():
    print("Loading test data...")
    data = prepare_splits()

    clf, reg = load_models()

    X_test = data["X_test"]
    y_test_c = data["y_test_class"]
    y_test_d = data["y_test_depth"]

    # === Classification ===
    print("\n" + "=" * 60)
    print("CLASSIFICATION METRICS (Flood Risk Level)")
    print("=" * 60)

    y_pred_c = clf.predict(X_test)
    y_proba = clf.predict_proba(X_test)

    accuracy = accuracy_score(y_test_c, y_pred_c)
    f1_weighted = f1_score(y_test_c, y_pred_c, average="weighted")
    f1_macro = f1_score(y_test_c, y_pred_c, average="macro")

    print(f"\nAccuracy:  {accuracy:.4f}")
    print(f"F1 (weighted): {f1_weighted:.4f}")
    print(f"F1 (macro):    {f1_macro:.4f}")

    # AUC-ROC
    try:
        auc = roc_auc_score(y_test_c, y_proba, multi_class="ovr", average="weighted")
        print(f"AUC-ROC (weighted): {auc:.4f}")
    except ValueError:
        auc = 0.0
        print("AUC-ROC: N/A")

    # Per-class report
    target_names = ["normal", "waspada", "tergenang"]
    present_classes = np.unique(np.concatenate([y_test_c, y_pred_c]))
    names = [target_names[i] for i in present_classes if i < len(target_names)]

    print(f"\nClassification Report:")
    print(classification_report(y_test_c, y_pred_c, target_names=names, zero_division=0))

    # Confusion matrix
    print("Confusion Matrix:")
    cm = confusion_matrix(y_test_c, y_pred_c)
    print(cm)

    # === Regression ===
    print("\n" + "=" * 60)
    print("REGRESSION METRICS (Water Depth)")
    print("=" * 60)

    y_pred_d = reg.predict(X_test)
    y_pred_d = np.clip(y_pred_d, 0, 200)

    mae = mean_absolute_error(y_test_d, y_pred_d)
    rmse = np.sqrt(mean_squared_error(y_test_d, y_pred_d))
    r2 = r2_score(y_test_d, y_pred_d)

    print(f"\nMAE:  {mae:.2f} cm")
    print(f"RMSE: {rmse:.2f} cm")
    print(f"R²:   {r2:.4f}")

    # Depth bucket accuracy
    def depth_bucket(depth):
        if depth < 20:
            return "<20cm"
        elif depth < 40:
            return "20-40cm"
        elif depth < 70:
            return "40-70cm"
        else:
            return ">70cm"

    actual_buckets = [depth_bucket(d) for d in y_test_d]
    pred_buckets = [depth_bucket(d) for d in y_pred_d]
    bucket_acc = sum(a == p for a, p in zip(actual_buckets, pred_buckets)) / len(actual_buckets)
    print(f"Depth Bucket Accuracy: {bucket_acc:.4f}")

    # === Summary ===
    results = {
        "test_size": len(X_test),
        "classification": {
            "accuracy": round(accuracy, 4),
            "f1_weighted": round(f1_weighted, 4),
            "f1_macro": round(f1_macro, 4),
            "auc_roc": round(auc, 4),
        },
        "regression": {
            "mae_cm": round(mae, 2),
            "rmse_cm": round(rmse, 2),
            "r2": round(r2, 4),
            "depth_bucket_accuracy": round(bucket_acc, 4),
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
