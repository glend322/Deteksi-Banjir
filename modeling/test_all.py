"""Quick verification of all modeling modules."""
import sys
sys.path.insert(0, r"C:\Users\Joshevan\Downloads\Deteksi-Banjir\modeling")

print("=== Module Import Tests ===")
modules = [
    "area_mapping", "classifier", "cv_model", "verifier",
    "route_engine", "evacuation_finder",
]
for m in modules:
    try:
        __import__(m)
        print(f"  OK  {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}")

print("\n=== Checkpoint Test ===")
import torch
from pathlib import Path
ckpt = Path(r"C:\Users\Joshevan\Downloads\Deteksi-Banjir\modeling\checkpoints\best.pt")
if ckpt.exists():
    data = torch.load(ckpt, map_location="cpu", weights_only=False)
    print(f"  OK  backbone={data['backbone']}, keys={list(data.keys())}")
else:
    print("  FAIL checkpoint not found")

print("\n=== Route Engine Test ===")
from route_engine import calculate_safe_routes
result = calculate_safe_routes(-7.0505, 110.4410, -6.9644, 110.4281, flood_zones=[
    {"lat": -6.9535, "lng": 110.4570, "radius_km": 1.5, "status": "impassable", "depth_cm": 60},
])
print(f"  OK  {len(result['options'])} route options, {result['flood_zones_active']} flood zones")

print("\n=== Classifier Test ===")
from classifier import classify_flood
for d in [5, 25, 50]:
    r = classify_flood(d, "Test Area")
    print(f"  OK  {d}cm -> {r.classification} -> {r.notification}")

print("\n=== Evacuation Finder Test ===")
from evacuation_finder import find_nearest_evacuation
evac = find_nearest_evacuation(-7.0505, 110.4410)
if evac:
    print(f"  OK  nearest: {evac['name']} ({evac['distance_km']}km)")
else:
    print("  FAIL no evacuation found")

print("\n=== Area Mapping Test ===")
from area_mapping import get_area_name
for lat, lng in [(-6.9535, 110.4570), (-6.9904, 110.4229), (-7.0505, 110.4410)]:
    name = get_area_name(lat, lng)
    print(f"  OK  ({lat}, {lng}) -> {name}")

print("\n=== CV Model Forward Pass Test ===")
from cv_model import FloodClassifier, depth_to_classification
model = FloodClassifier(num_classes=2, pretrained=False, backbone="mobilenet_v3_small")
model.eval()
dummy = torch.randn(1, 3, 224, 224)
with torch.no_grad():
    out = model(dummy)
probs = torch.softmax(out["logits"], dim=1).numpy()[0]
depth = float(out["depth_cm"].numpy()[0])
cls = depth_to_classification(depth)
print(f"  OK  flood_prob={probs[1]:.4f}, depth={depth:.1f}cm, class={cls}")

print("\n=== All tests passed ===")
