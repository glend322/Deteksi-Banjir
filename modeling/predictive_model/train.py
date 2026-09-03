"""
Train the predictive flood model.

Trains two heads:
1. Classification: flood risk level (normal/waspada/tergenang)
2. Regression: estimated water depth (cm)

Models: XGBoost (primary), with LightGBM as alternative.
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
    f1_score,
)
from sklearn.utils.class_weight import compute_class_weight
from xgboost import XGBClassifier, XGBRegressor

sys.path.insert(0, str(Path(__file__).parent))
from dataset import prepare_splits

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


def train_classifier(X_train, y_train, X_val, y_val, feature_names):
    print("=== Training Classification Model (Flood Risk Level) ===")

    # Handle class imbalance
    classes = np.unique(y_train)
    weights = compute_class_weight("balanced", classes=classes, y=y_train)
    sample_weights = np.array([weights[c] for c in y_train])

    clf = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="multi:softprob",
        num_class=len(classes),
        eval_metric="mlogloss",
        early_stopping_rounds=50,
        random_state=42,
        use_label_encoder=False,
    )

    clf.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    # Evaluate on val
    y_pred = clf.predict(X_val)
    y_proba = clf.predict_proba(X_val)

    print("\nValidation Classification Report:")
    target_names = ["normal", "waspada", "tergenang"]
    print(classification_report(y_val, y_pred, target_names=target_names[:len(classes)]))

    print("Confusion Matrix:")
    print(confusion_matrix(y_val, y_pred))

    # AUC-ROC (one-vs-rest)
    try:
        auc = roc_auc_score(y_val, y_proba, multi_class="ovr", average="weighted")
        print(f"\nWeighted AUC-ROC: {auc:.4f}")
    except ValueError:
        auc = 0.0
        print("AUC-ROC: N/A (single class in val)")

    f1 = f1_score(y_val, y_pred, average="weighted")
    print(f"Weighted F1: {f1:.4f}")

    return clf, {"auc_roc": auc, "f1": f1}


def train_regressor(X_train, y_train, X_val, y_val, feature_names):
    print("\n=== Training Regression Model (Water Depth) ===")

    reg = XGBRegressor(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective="reg:squarederror",
        eval_metric="rmse",
        early_stopping_rounds=50,
        random_state=42,
    )

    reg.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    y_pred = reg.predict(X_val)
    mae = mean_absolute_error(y_val, y_pred)
    rmse = np.sqrt(np.mean((y_val - y_pred) ** 2))

    print(f"\nValidation MAE: {mae:.2f} cm")
    print(f"Validation RMSE: {rmse:.2f} cm")

    return reg, {"mae": mae, "rmse": rmse}


def main():
    print("Loading data...")
    data = prepare_splits()

    clf, clf_metrics = train_classifier(
        data["X_train"], data["y_train_class"],
        data["X_val"], data["y_val_class"],
        data["feature_names"],
    )

    reg, reg_metrics = train_regressor(
        data["X_train"], data["y_train_depth"],
        data["X_val"], data["y_val_depth"],
        data["feature_names"],
    )

    # Save models
    clf_path = CHECKPOINT_DIR / "classifier.pkl"
    with open(clf_path, "wb") as f:
        pickle.dump(clf, f)
    print(f"\nSaved classifier: {clf_path}")

    reg_path = CHECKPOINT_DIR / "regressor.pkl"
    with open(reg_path, "wb") as f:
        pickle.dump(reg, f)
    print(f"Saved regressor: {reg_path}")

    # Save scaler
    scaler_path = CHECKPOINT_DIR / "scaler.pkl"
    with open(scaler_path, "wb") as f:
        pickle.dump(data["scaler"], f)
    print(f"Saved scaler: {scaler_path}")

    # Save feature names
    meta = {
        "feature_names": data["feature_names"],
        "classifier_metrics": clf_metrics,
        "regressor_metrics": reg_metrics,
        "train_size": len(data["X_train"]),
        "val_size": len(data["X_val"]),
        "test_size": len(data["X_test"]),
    }
    meta_path = CHECKPOINT_DIR / "model_meta.json"
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Saved metadata: {meta_path}")

    # Feature importance
    importance = pd.DataFrame({
        "feature": data["feature_names"],
        "importance": clf.feature_importances_,
    }).sort_values("importance", ascending=False)
    print(f"\nFeature Importance (Classifier):")
    print(importance.to_string(index=False))

    print("\nTraining complete!")


if __name__ == "__main__":
    main()
