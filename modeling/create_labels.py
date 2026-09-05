import json, os
from pathlib import Path

DATA_DIR = Path(r"C:\Users\Joshevan\Downloads\Deteksi-Banjir\modeling\data\training")
labels = {}

for f in sorted((DATA_DIR / "flood_river").glob("*.*")):
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        labels["flood_river/" + f.name] = {"flood": 1, "river": 1, "trash": 0}

for f in sorted((DATA_DIR / "flood_trash").glob("*.*")):
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        labels["flood_trash/" + f.name] = {"flood": 1, "river": 0, "trash": 1}

for f in sorted((DATA_DIR / "flood_rain").glob("*.*")):
    if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        labels["flood_rain/" + f.name] = {"flood": 1, "river": 0, "trash": 0}

for cls in ["flood", "nonflood"]:
    cls_dir = DATA_DIR / cls
    if cls_dir.exists():
        for f in sorted(cls_dir.glob("*.*")):
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                labels[cls + "/" + f.name] = {"flood": 0, "river": 0, "trash": 0}

out_path = DATA_DIR / "cause_labels.json"
with open(out_path, "w") as fp:
    json.dump(labels, fp, indent=2)

river_count = sum(1 for v in labels.values() if v["river"] == 1)
trash_count = sum(1 for v in labels.values() if v["trash"] == 1)
flood_count = sum(1 for v in labels.values() if v["flood"] == 1)
noflood_count = sum(1 for v in labels.values() if v["flood"] == 0)

print(f"Total labels: {len(labels)}")
print(f"  River: {river_count}")
print(f"  Trash: {trash_count}")
print(f"  Flood: {flood_count}")
print(f"  No flood: {noflood_count}")
