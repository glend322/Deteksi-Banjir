"""
CV Flood Image Classifier - Dataset

Supports two modes:
1. Real images: expects folder structure per class
2. Synthetic fallback: generates colored noise images for pipeline testing

Expected folder structure (real mode):
  data_dir/
    normal/
      img_001.jpg
      img_002.jpg
    waspada/
      img_001.jpg
    tergenang/
      img_001.jpg
    tidak_dapat_dilalui/
      img_001.jpg

Each image filename can optionally have a depth suffix: img_001_depth55.jpg
"""
import json
import random
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from PIL import Image, ImageDraw
from torchvision import transforms

SEVERITY_CLASSES = ["normal", "waspada", "tergenang", "tidak_dapat_dilalui"]
CLASS_TO_IDX = {c: i for i, c in enumerate(SEVERITY_CLASSES)}

DEPTH_RANGES = {
    "normal": (0, 10),
    "waspada": (5, 25),
    "tergenang": (20, 60),
    "tidak_dapat_dilalui": (50, 150),
}


class SyntheticFloodDataset(Dataset):
    """Generate synthetic flood images for pipeline testing."""

    def __init__(self, samples: list[dict], image_size: int = 224, augment: bool = False):
        self.samples = samples
        self.image_size = image_size
        self.augment = augment
        self.transform = self._build_transforms(augment)

    def _build_transforms(self, augment: bool) -> transforms.Compose:
        t = [
            transforms.Resize((self.image_size, self.image_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
        return transforms.Compose(t)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict]:
        s = self.samples[idx]
        label = CLASS_TO_IDX[s["label"]]
        depth_cm = float(s["depth_cm"])

        # Generate synthetic image based on class
        img = self._generate_image(label, depth_cm)
        img = self.transform(img)

        return img, {"label": label, "depth_cm": depth_cm}

    def _generate_image(self, label: int, depth_cm: float) -> Image.Image:
        """Generate a colored image that roughly encodes flood severity."""
        w, h = self.image_size, self.image_size
        rng = np.random.RandomState()

        if label == 0:  # normal - grey road, no water
            bg = rng.randint(80, 130, (h, w, 3), dtype=np.uint8)
        elif label == 1:  # waspada - some blue patches
            bg = rng.randint(80, 130, (h, w, 3), dtype=np.uint8)
            blue_patch = rng.randint(0, 2, (h, w), dtype=bool)
            bg[blue_patch, 0] = 40
            bg[blue_patch, 1] = 80
            bg[blue_patch, 2] = 150
        elif label == 2:  # tergenang - large blue area
            bg = rng.randint(60, 100, (h, w, 3), dtype=np.uint8)
            blue_ratio = min(depth_cm / 80.0, 0.8)
            blue_mask = rng.random((h, w)) < blue_ratio
            bg[blue_mask, 0] = 30
            bg[blue_mask, 1] = 60
            bg[blue_mask, 2] = 140
        else:  # tidak_dapat_dilalui - mostly submerged
            bg = rng.randint(40, 80, (h, w, 3), dtype=np.uint8)
            blue_mask = rng.random((h, w)) < 0.85
            bg[blue_mask, 0] = 20
            bg[blue_mask, 1] = 50
            bg[blue_mask, 2] = 120

        img = Image.fromarray(bg, "RGB")

        if self.augment:
            jitter = transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3)
            img = jitter(img)

        return img


class FloodImageDataset(Dataset):
    """Load real flood images from directory structure."""

    def __init__(self, samples: list[dict], image_size: int = 224, augment: bool = False):
        self.samples = samples
        self.image_size = image_size
        self.transform = self._build_transforms(augment)

    def _build_transforms(self, augment: bool) -> transforms.Compose:
        t = []
        if augment:
            t.extend([
                transforms.RandomHorizontalFlip(),
                transforms.RandomRotation(15),
                transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
                transforms.RandomResizedCrop(self.image_size, scale=(0.8, 1.0)),
            ])
        else:
            t.append(transforms.Resize((self.image_size, self.image_size)))

        t.extend([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        return transforms.Compose(t)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, dict]:
        s = self.samples[idx]
        img = Image.open(s["path"]).convert("RGB")
        img = self.transform(img)
        return img, {"label": s["label"], "depth_cm": s["depth_cm"]}


def scan_image_dir(data_dir: Path) -> list[dict]:
    """Scan directory for images with optional depth in filename."""
    samples = []
    for class_name in SEVERITY_CLASSES:
        class_dir = data_dir / class_name
        if not class_dir.exists():
            continue
        for img_path in class_dir.iterdir():
            if img_path.suffix.lower() not in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
                continue
            depth_cm = _parse_depth_from_filename(img_path.stem)
            samples.append({
                "path": str(img_path),
                "label": class_name,
                "label_idx": CLASS_TO_IDX[class_name],
                "depth_cm": depth_cm,
            })
    return samples


def _parse_depth_from_filename(stem: str) -> float:
    """Try to extract depth from filename like 'img_001_depth55'."""
    import re
    m = re.search(r"depth(\d+)", stem)
    if m:
        return float(m.group(1))
    lo, hi = DEPTH_RANGES.get("normal", (0, 10))
    return random.uniform(lo, hi)


def generate_synthetic_samples(n_per_class: int = 50) -> list[dict]:
    """Generate synthetic sample metadata for pipeline testing."""
    samples = []
    for class_name in SEVERITY_CLASSES:
        lo, hi = DEPTH_RANGES[class_name]
        for i in range(n_per_class):
            depth = random.uniform(lo, hi)
            samples.append({
                "path": f"synthetic_{class_name}_{i:04d}",
                "label": class_name,
                "label_idx": CLASS_TO_IDX[class_name],
                "depth_cm": depth,
            })
    return samples


def prepare_dataloaders(
    data_dir: str | Path | None = None,
    image_size: int = 224,
    batch_size: int = 32,
    train_split: float = 0.8,
    val_split: float = 0.1,
    augment: bool = True,
    seed: int = 42,
) -> dict:
    """Create train/val/test dataloaders.

    If data_dir is None or has no images, uses synthetic data.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    use_real = False
    if data_dir is not None:
        data_dir = Path(data_dir)
        if data_dir.exists():
            samples = scan_image_dir(data_dir)
            if len(samples) > 0:
                use_real = True

    if not use_real:
        print("[dataset] No real images found, using synthetic data for pipeline testing")
        samples = generate_synthetic_samples(n_per_class=200)

    random.shuffle(samples)

    total = len(samples)
    n_train = int(total * train_split)
    n_val = int(total * val_split)

    train_samples = samples[:n_train]
    val_samples = samples[n_train:n_train + n_val]
    test_samples = samples[n_train + n_val:]

    print(f"[dataset] Train: {len(train_samples)}, Val: {len(val_samples)}, Test: {len(test_samples)}")
    for cls in SEVERITY_CLASSES:
        count = sum(1 for s in train_samples if s["label"] == cls)
        print(f"  train/{cls}: {count}")

    if use_real:
        train_ds = FloodImageDataset(train_samples, image_size, augment=augment)
        val_ds = FloodImageDataset(val_samples, image_size, augment=False)
        test_ds = FloodImageDataset(test_samples, image_size, augment=False)
    else:
        train_ds = SyntheticFloodDataset(train_samples, image_size, augment=augment)
        val_ds = SyntheticFloodDataset(val_samples, image_size, augment=False)
        test_ds = SyntheticFloodDataset(test_samples, image_size, augment=False)

    # Class-balanced sampling for training
    class_counts = np.bincount([s["label_idx"] for s in train_samples], minlength=4)
    class_weights = 1.0 / (class_counts + 1e-6)
    sample_weights = [class_weights[s["label_idx"]] for s in train_samples]
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(train_samples), replacement=True)

    use_pin_memory = torch.cuda.is_available()
    train_loader = DataLoader(train_ds, batch_size=batch_size, sampler=sampler, num_workers=0, pin_memory=use_pin_memory)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    return {
        "train": train_loader,
        "val": val_loader,
        "test": test_loader,
        "train_samples": train_samples,
        "val_samples": val_samples,
        "test_samples": test_samples,
        "use_real": use_real,
    }


if __name__ == "__main__":
    data = prepare_dataloaders(image_size=224, batch_size=16)
    print(f"\nMode: {'real' if data['use_real'] else 'synthetic'}")

    imgs, targets = next(iter(data["train"]))
    print(f"Batch shape: {imgs.shape}")
    print(f"Labels: {targets['label'][:5]}")
    print(f"Depths: {targets['depth_cm'][:5]}")
