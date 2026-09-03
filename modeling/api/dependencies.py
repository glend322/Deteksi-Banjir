"""
Dependencies for FastAPI — model loading and shared state.
"""
import sys
from pathlib import Path

# Add predictive_model to path
MODEL_DIR = Path(__file__).parent.parent / "predictive_model"
sys.path.insert(0, str(MODEL_DIR))

import pickle
from dataset import load_data, add_temporal_features, FEATURE_COLS

_clf = None
_reg = None
_scaler = None
_df = None


def get_models():
    global _clf, _reg, _scaler
    if _clf is None:
        ckpt = MODEL_DIR / "checkpoints"
        with open(ckpt / "classifier.pkl", "rb") as f:
            _clf = pickle.load(f)
        with open(ckpt / "regressor.pkl", "rb") as f:
            _reg = pickle.load(f)
        with open(ckpt / "scaler.pkl", "rb") as f:
            _scaler = pickle.load(f)
    return _clf, _reg, _scaler


def get_data():
    global _df
    if _df is None:
        _df = load_data()
        _df = add_temporal_features(_df)
    return _df


def get_feature_cols():
    return FEATURE_COLS + ["day_of_week", "month", "day_of_year", "is_rainy_season"]
