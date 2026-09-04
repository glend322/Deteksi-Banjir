"""
CV Flood Detection — Training Script

Train the FloodClassifier on flood image datasets.

Usage:
  python train.py
  python train.py --data_dir data/raw/flood_images --epochs 30 --backbone mobilenet_v3_small
"""
import argparse
import logging
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, random_split
from torchvision import transforms
from PIL import Image

ROOT_DIR = Path(__file__).parent
CHECKPOINT_DIR = ROOT_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("trainer")

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


class FloodImageDataset(Dataset):
    """
    Dataset for flood image classification.

    Expected directory structure:
      data_dir/
        no_flood/
          img1.jpg
          img2.jpg
        flood/
          img1.jpg
          img2.jpg

    If no data directory exists, generates synthetic data for demo.
    """

    def __init__(self, data_dir: str, transform=None):
        self.data_dir = Path(data_dir)
        self.transform = transform
        self.samples = []

        if self.data_dir.exists():
            self._load_real_data()
        else:
            logger.warning(f"Data dir {data_dir} not found, using synthetic data")
            self._generate_synthetic(200)

    def _load_real_data(self):
        class_map = {"no_flood": 0, "nonflood": 0, "flood": 1}
        for class_name, label in class_map.items():
            class_dir = self.data_dir / class_name
            if not class_dir.exists():
                continue
            for img_path in class_dir.glob("*"):
                if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
                    self.samples.append((str(img_path), label))

        logger.info(f"Loaded {len(self.samples)} images: "
                     f"{sum(1 for _, l in self.samples if l == 0)} no_flood, "
                     f"{sum(1 for _, l in self.samples if l == 1)} flood")

    def _generate_synthetic(self, n: int):
        for i in range(n):
            img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
            label = random.choice([0, 1])
            self.samples.append((img, label))

        logger.info(f"Generated {n} synthetic samples for demo training")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path_or_array, label = self.samples[idx]

        if isinstance(path_or_array, str):
            img = Image.open(path_or_array).convert("RGB")
        else:
            img = Image.fromarray(path_or_array)

        if self.transform:
            img = self.transform(img)

        return img, torch.tensor(label, dtype=torch.long)


class SyntheticDepthDataset(Dataset):
    """Synthetic depth estimation dataset for demo training."""

    def __init__(self, n: int = 200, transform=None):
        self.n = n
        self.transform = transform
        self.depths = [random.uniform(0, 100) for _ in range(n)]

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        img = Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8))
        if self.transform:
            img = self.transform(img)
        depth = torch.tensor(self.depths[idx], dtype=torch.float32)
        return img, depth


def get_transforms():
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    return train_transform, val_transform


def train_one_epoch(model, loader, criterion_cls, criterion_depth, optimizer, device, cls_weight=0.7, depth_weight=0.3):
    model.train()
    total_loss = 0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        out = model(images)

        loss_cls = criterion_cls(out["logits"], labels)
        loss = loss_cls
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        preds = out["logits"].argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += images.size(0)

    avg_loss = total_loss / total if total > 0 else 0
    accuracy = correct / total if total > 0 else 0
    return avg_loss, accuracy


@torch.no_grad()
def evaluate(model, loader, criterion_cls, device):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0

    for images, labels in loader:
        images = images.to(device)
        labels = labels.to(device)

        out = model(images)
        loss = criterion_cls(out["logits"], labels)

        total_loss += loss.item() * images.size(0)
        preds = out["logits"].argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += images.size(0)

    avg_loss = total_loss / total if total > 0 else 0
    accuracy = correct / total if total > 0 else 0
    return avg_loss, accuracy


def main():
    parser = argparse.ArgumentParser(description="Train Flood Classifier")
    parser.add_argument("--data_dir", type=str, default="data/training", help="Path to image data")
    parser.add_argument("--epochs", type=int, default=20, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    parser.add_argument("--backbone", type=str, default="mobilenet_v3_small", help="CNN backbone")
    parser.add_argument("--save_best", action="store_true", default=True, help="Save best model")
    args = parser.parse_args()

    from cv_model import FloodClassifier

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    train_transform, val_transform = get_transforms()

    full_dataset = FloodImageDataset(args.data_dir, transform=train_transform)
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_subset = random_split(full_dataset, [train_size, val_size])

    val_dataset = FloodImageDataset(args.data_dir, transform=val_transform)
    _, val_dataset = random_split(val_dataset, [train_size, val_size])

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = FloodClassifier(num_classes=2, pretrained=True, backbone=args.backbone)
    model.to(device)

    flood_count = sum(1 for _, l in full_dataset.samples if l == 1)
    nonflood_count = sum(1 for _, l in full_dataset.samples if l == 0)
    total = flood_count + nonflood_count
    class_weights = torch.tensor([total / nonflood_count, total / flood_count], dtype=torch.float32).to(device)
    criterion_cls = nn.CrossEntropyLoss(weight=class_weights)
    logger.info(f"Class weights: nonflood={class_weights[0]:.2f}, flood={class_weights[1]:.2f}")

    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=0.0001)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    best_val_acc = 0.0

    logger.info(f"Training {args.backbone} for {args.epochs} epochs on {train_size} images")

    for epoch in range(args.epochs):
        train_loss, train_acc = train_one_epoch(model, train_loader, criterion_cls, None, optimizer, device)
        val_loss, val_acc = evaluate(model, val_loader, criterion_cls, device)
        scheduler.step()

        logger.info(
            f"Epoch {epoch+1}/{args.epochs} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f}"
        )

        if val_acc > best_val_acc and args.save_best:
            best_val_acc = val_acc
            checkpoint = {
                "model_state_dict": model.state_dict(),
                "backbone": args.backbone,
                "num_classes": 2,
                "val_acc": val_acc,
                "epoch": epoch + 1,
            }
            save_path = CHECKPOINT_DIR / "best.pt"
            torch.save(checkpoint, save_path)
            logger.info(f"Saved best model to {save_path} (val_acc={val_acc:.4f})")

    logger.info(f"Training complete. Best val accuracy: {best_val_acc:.4f}")


if __name__ == "__main__":
    main()
