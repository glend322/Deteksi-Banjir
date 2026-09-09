"""
Quick verification test for flood depth classification changes.
Run: python test_classification.py
"""
import sys
sys.path.insert(0, ".")


def test_unified_thresholds():
    from detection.cv_model import DANGKAL_MAX_CM, SEDANG_MAX_CM, DEPTH_MAX_CM
    assert DANGKAL_MAX_CM == 20.0, f"Expected 20.0, got {DANGKAL_MAX_CM}"
    assert SEDANG_MAX_CM == 40.0, f"Expected 40.0, got {SEDANG_MAX_CM}"
    assert DEPTH_MAX_CM == 200.0
    print("[PASS] Unified thresholds defined correctly")


def test_depth_to_classification():
    from detection.cv_model import depth_to_classification
    assert depth_to_classification(0) == "dangkal"
    assert depth_to_classification(10) == "dangkal"
    assert depth_to_classification(19.9) == "dangkal"
    assert depth_to_classification(20) == "sedang"
    assert depth_to_classification(30) == "sedang"
    assert depth_to_classification(39.9) == "sedang"
    assert depth_to_classification(40) == "dalam"
    assert depth_to_classification(70) == "dalam"
    assert depth_to_classification(200) == "dalam"
    print("[PASS] depth_to_classification works correctly")


def test_depth_cm_to_class():
    from detection.cv_model import depth_cm_to_class
    assert depth_cm_to_class(0) == 0
    assert depth_cm_to_class(15) == 0
    assert depth_cm_to_class(20) == 1
    assert depth_cm_to_class(35) == 1
    assert depth_cm_to_class(40) == 2
    assert depth_cm_to_class(100) == 2
    print("[PASS] depth_cm_to_class works correctly")


def test_depth_buckets_consistent():
    from detection.cv_model import DEPTH_BUCKETS, DEPTH_BUCKET_LABELS, DANGKAL_MAX_CM, SEDANG_MAX_CM
    assert DEPTH_BUCKETS[0] == (0, DANGKAL_MAX_CM)
    assert DEPTH_BUCKETS[1] == (DANGKAL_MAX_CM, SEDANG_MAX_CM)
    print("[PASS] Depth buckets consistent with constants")


def test_depth_regressor_head():
    import torch
    from detection.cv_model import FloodClassifier
    model = FloodClassifier(num_classes=2, num_causes=2, pretrained=False, backbone="mobilenet_v3_small")
    x = torch.randn(1, 3, 224, 224)
    out = model(x)
    assert "depth_value" in out, "depth_value not in model output"
    assert out["depth_value"].shape == (1, 1), f"Unexpected shape: {out['depth_value'].shape}"
    assert (out["depth_value"] >= 0).all(), "depth_value should be >= 0 (ReLU)"
    print("[PASS] Depth regressor head works")


def test_checkpoint_loads_with_strict_false():
    import torch
    from pathlib import Path
    from detection.cv_model import FloodClassifier
    ckpt_path = Path("checkpoints/best.pt")
    if not ckpt_path.exists():
        print("[SKIP] No checkpoint found, skipping load test")
        return
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    backbone = ckpt.get("backbone", "resnet50")
    model = FloodClassifier(num_classes=2, num_causes=2, pretrained=False, backbone=backbone)
    model.load_state_dict(ckpt["model_state_dict"], strict=False)
    print("[PASS] Checkpoint loads with strict=False")


def test_classifier_import():
    from detection.classifier import classify_flood, STATUS_MAP, COLOR_MAP
    result = classify_flood("dangkal", "Kaligawe", "sungai meluap", river_detected=True)
    assert result.status == "watch"
    assert result.color == "#F59E0B"
    assert "dangkal" in result.notification
    print("[PASS] Classifier works with shared thresholds")


def test_verifier_min_depth():
    from detection.verifier import FalsePositiveFilter
    f = FalsePositiveFilter()
    assert f.min_depth_cm == 5.0, f"Expected 5.0, got {f.min_depth_cm}"
    print("[PASS] Verifier min_depth_cm lowered to 5.0")


def test_cause_to_text():
    from detection.cv_model import cause_to_text
    assert cause_to_text({"river": 0.9, "trash": 0.1}) == "sungai meluap"
    assert cause_to_text({"river": 0.1, "trash": 0.9}) == "sampah menyumbat saluran"
    assert cause_to_text({"river": 0.9, "trash": 0.9}) == "sungai meluap dan sampah menyumbat"
    assert cause_to_text({"river": 0.1, "trash": 0.1}) == "genangan air hujan"
    print("[PASS] cause_to_text works correctly")


if __name__ == "__main__":
    tests = [
        test_unified_thresholds,
        test_depth_to_classification,
        test_depth_cm_to_class,
        test_depth_buckets_consistent,
        test_depth_regressor_head,
        test_checkpoint_loads_with_strict_false,
        test_classifier_import,
        test_verifier_min_depth,
        test_cause_to_text,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {test.__name__}: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed == 0:
        print("All tests passed!")
    else:
        sys.exit(1)
