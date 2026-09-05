"""
CV Flood Detection — Training Script with Cause Detection

Multi-label cause detection:
- river: sungai meluap
- trash: sampah menyumbat saluran

Usage:
  python train.py
  python train.py --data_dir data/training --epochs 30 --backbone mobilenet_v3_small
"""
import argparse
import json
import logging
import os
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
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
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False


class FloodImageDataset(Dataset):
    """
    Dataset for flood classification + cause detection.

    Expected directory structure:
      data_dir/
        nonflood/
          img1.jpg
        flood/
          img1.jpg
        flood_river/
          img1.jpg
        flood_trash/
          img1.jpg

    Labels:
      - nonflood: flood=0, cause=[0,0]
      - flood: flood=1, cause=[0,0] (genangan air hujan)
      - flood_river: flood=1, cause=[1,0] (sungai meluap)
      - flood_trash: flood=1, cause=[0,1] (sampah menyumbat)
    """

    CAUSE_MAP = {
        "flood_river": [1.0, 0.0],
        "flood_trash": [0.0, 1.0],
        "flood": [0.0, 0.0],
    }

    def __init__(self, data_dir: str, transform=None, samples=None):
        self.data_dir = Path(data_dir)
        self.transform = transform
        self.samples = samples or []

        if not self.samples:
            self._load_data()

    def _load_data(self):
        class_map = {
            "no_flood": 0,
            "nonflood": 0,
            "flood": 1,
            "flood_river": 1,
            "flood_trash": 1,
        }

        for class_name, flood_label in class_map.items():
            class_dir = self.data_dir / class_name
            if not class_dir.exists():
                continue
            for img_path in class_dir.glob("*"):
                if img_path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                    if flood_label == 0:
                        depth = 0.0
                        cause = [0.0, 0.0]
                    else:
                        depth = 30.0
                        cause = self.CAUSE_MAP.get(class_name, [0.0, 0.0])
                    self.samples.append((str(img_path), flood_label, depth, cause))

        flood_count = sum(1 for _, l, _, _ in self.samples if l == 1)
        noflood_count = sum(1 for _, l, _, _ in self.samples if l == 0)
        river_count = sum(1 for _, _, _, c in self.samples if c[0] > 0)
        trash_count = sum(1 for _, _, _, c in self.samples if c[1] > 0)

        logger.info(f"Loaded {len(self.samples)} images: "
                     f"{noflood_count} no_flood, {flood_count} flood "
                     f"(river={river_count}, trash={trash_count})")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label, depth, cause = self.samples[idx]

        try:
            img = Image.open(path).convert("RGB")
        except Exception:
            img = Image.new("RGB", (224, 224), (128, 128, 128))

        if self.transform:
            img = self.transform(img)

        return (
            img,
            torch.tensor(label, dtype=torch.long),
            torch.tensor(depth, dtype=torch.float32),
            torch.tensor(cause, dtype=torch.float32),
        )


def get_transforms(mode="train"):
    if mode == "train":
        return transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomCrop(224),
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.RandomVerticalFlip(p=0.3),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
            transforms.RandomGrayscale(p=0.1),
            transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            transforms.RandomErasing(p=0.2, scale=(0.02, 0.15)),
        ])
    else:
        return transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


def create_splits(dataset, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    from collections import defaultdict

    class_samples = defaultdict(list)
    for idx, (_, label, _, _) in enumerate(dataset.samples):
        class_samples[label].append(idx)

    train_indices, val_indices, test_indices = [], [], []

    for label, indices in class_samples.items():
        random.shuffle(indices)
        n = len(indices)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        train_indices.extend(indices[:n_train])
        val_indices.extend(indices[n_train:n_train + n_val])
        test_indices.extend(indices[n_train + n_val:])

    random.shuffle(train_indices)
    random.shuffle(val_indices)
    random.shuffle(test_indices)

    return train_indices, val_indices, test_indices


class LabelSmoothingCrossEntropy(nn.Module):
    def __init__(self, smoothing=0.1):
        super().__init__()
        self.smoothing = smoothing

    def forward(self, pred, target):
        n_classes = pred.size(-1)
        log_preds = torch.log_softmax(pred, dim=-1)

        nll_loss = -log_preds.gather(dim=-1, index=target.unsqueeze(1)).squeeze(1)
        smooth_loss = -log_preds.mean(dim=-1)

        loss = (1 - self.smoothing) * nll_loss + self.smoothing * smooth_loss
        return loss.mean()


def train_one_epoch(model, loader, criterion_cls, criterion_depth, criterion_cause,
                    optimizer, device, cls_weight=0.4, depth_weight=0.1, cause_weight=0.5):
    model.train()
    total_loss = 0
    correct = 0
    total = 0
    depth_errors = []
    cause_correct = 0
    cause_total = 0

    for images, labels, depths, causes in loader:
        images = images.to(device)
        labels = labels.to(device)
        depths = depths.to(device)
        causes = causes.to(device)

        optimizer.zero_grad()
        out = model(images)

        loss_cls = criterion_cls(out["logits"], labels)
        loss_depth = criterion_depth(out["depth_cm"], depths)
        loss_cause = criterion_cause(out["cause_logits"], causes)
        loss = cls_weight * loss_cls + depth_weight * loss_depth + cause_weight * loss_cause

        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        total_loss += loss.item() * images.size(0)
        preds = out["logits"].argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += images.size(0)
        depth_errors.extend(torch.abs(out["depth_cm"] - depths).cpu().detach().numpy().tolist())

        cause_preds = (torch.sigmoid(out["cause_logits"]) > 0.5).float()
        cause_correct += (cause_preds == causes).all(dim=1).sum().item()
        cause_total += images.size(0)

    avg_loss = total_loss / total if total > 0 else 0
    accuracy = correct / total if total > 0 else 0
    avg_depth_mae = np.mean(depth_errors) if depth_errors else 0
    cause_acc = cause_correct / cause_total if cause_total > 0 else 0
    return avg_loss, accuracy, avg_depth_mae, cause_acc


@torch.no_grad()
def evaluate(model, loader, criterion_cls, criterion_depth, criterion_cause, device):
    model.eval()
    total_loss = 0
    correct = 0
    total = 0
    depth_errors = []
    cause_correct = 0
    cause_total = 0
    all_preds = []
    all_labels = []
    all_cause_preds = []
    all_cause_labels = []

    for images, labels, depths, causes in loader:
        images = images.to(device)
        labels = labels.to(device)
        depths = depths.to(device)
        causes = causes.to(device)

        out = model(images)
        loss_cls = criterion_cls(out["logits"], labels)

        total_loss += loss_cls.item() * images.size(0)
        preds = out["logits"].argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += images.size(0)
        depth_errors.extend(torch.abs(out["depth_cm"] - depths).cpu().detach().numpy().tolist())

        cause_preds = (torch.sigmoid(out["cause_logits"]) > 0.5).float()
        cause_correct += (cause_preds == causes).all(dim=1).sum().item()
        cause_total += images.size(0)

        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())
        all_cause_preds.extend(cause_preds.cpu().numpy())
        all_cause_labels.extend(causes.cpu().numpy())

    avg_loss = total_loss / total if total > 0 else 0
    accuracy = correct / total if total > 0 else 0
    avg_depth_mae = np.mean(depth_errors) if depth_errors else 0
    cause_acc = cause_correct / cause_total if cause_total > 0 else 0

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    tp = ((all_preds == 1) & (all_labels == 1)).sum()
    fp = ((all_preds == 1) & (all_labels == 0)).sum()
    fn = ((all_preds == 0) & (all_labels == 1)).sum()
    tn = ((all_preds == 0) & (all_labels == 0)).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    all_cause_preds = np.array(all_cause_preds)
    all_cause_labels = np.array(all_cause_labels)
    river_acc = (all_cause_preds[:, 0] == all_cause_labels[:, 0]).mean() if len(all_cause_preds) > 0 else 0
    trash_acc = (all_cause_preds[:, 1] == all_cause_labels[:, 1]).mean() if len(all_cause_preds) > 0 else 0

    return avg_loss, accuracy, avg_depth_mae, cause_acc, {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "tn": int(tn),
        "river_acc": river_acc,
        "trash_acc": trash_acc,
    }


class EarlyStopping:
    def __init__(self, patience=10, min_delta=0.001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = None
        self.should_stop = False

    def __call__(self, val_loss):
        if self.best_loss is None:
            self.best_loss = val_loss
        elif val_loss < self.best_loss - self.min_delta:
            self.best_loss = val_loss
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                self.should_stop = True


def main():
    parser = argparse.ArgumentParser(description="Train Flood Classifier + Cause Detection")
    parser.add_argument("--data_dir", type=str, default="data/training")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch_size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=0.001)
    parser.add_argument("--weight_decay", type=float, default=0.01)
    parser.add_argument("--backbone", type=str, default="mobilenet_v3_small")
    parser.add_argument("--label_smoothing", type=float, default=0.1)
    parser.add_argument("--dropout", type=float, default=0.4)
    parser.add_argument("--cls_weight", type=float, default=0.4)
    parser.add_argument("--depth_weight", type=float, default=0.1)
    parser.add_argument("--cause_weight", type=float, default=0.5)
    args = parser.parse_args()

    from detection.cv_model import FloodClassifier

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"Using device: {device}")

    full_dataset = FloodImageDataset(args.data_dir)
    train_indices, val_indices, test_indices = create_splits(full_dataset)

    logger.info(f"Splits: train={len(train_indices)}, val={len(val_indices)}, test={len(test_indices)}")

    train_dataset = FloodImageDataset(args.data_dir, transform=get_transforms("train"),
                                       samples=[full_dataset.samples[i] for i in train_indices])
    val_dataset = FloodImageDataset(args.data_dir, transform=get_transforms("val"),
                                     samples=[full_dataset.samples[i] for i in val_indices])
    test_dataset = FloodImageDataset(args.data_dir, transform=get_transforms("test"),
                                      samples=[full_dataset.samples[i] for i in test_indices])

    train_labels = [full_dataset.samples[i][1] for i in train_indices]
    class_counts = np.bincount(train_labels)
    class_weights = 1.0 / class_counts
    sample_weights = [class_weights[label] for label in train_labels]
    sampler = WeightedRandomSampler(sample_weights, len(sample_weights))

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, sampler=sampler, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_dataset, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = FloodClassifier(num_classes=2, num_causes=2, pretrained=True, backbone=args.backbone)

    for name, module in model.named_modules():
        if isinstance(module, nn.Dropout):
            module.p = args.dropout

    model.to(device)

    criterion_cls = LabelSmoothingCrossEntropy(smoothing=args.label_smoothing)
    criterion_depth = nn.L1Loss()
    criterion_cause = nn.BCEWithLogitsLoss()

    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2)
    early_stopping = EarlyStopping(patience=10, min_delta=0.001)

    best_val_f1 = 0.0
    best_cause_acc = 0.0

    logger.info(f"Training {args.backbone} for up to {args.epochs} epochs")
    logger.info(f"Data: {len(train_dataset)} train, {len(val_dataset)} val, {len(test_dataset)} test")
    logger.info(f"Weights: cls={args.cls_weight}, depth={args.depth_weight}, cause={args.cause_weight}")

    for epoch in range(args.epochs):
        train_loss, train_acc, train_depth_mae, train_cause_acc = train_one_epoch(
            model, train_loader, criterion_cls, criterion_depth, criterion_cause, optimizer, device,
            cls_weight=args.cls_weight, depth_weight=args.depth_weight, cause_weight=args.cause_weight
        )
        val_loss, val_acc, val_depth_mae, val_cause_acc, val_metrics = evaluate(
            model, val_loader, criterion_cls, criterion_depth, criterion_cause, device
        )
        scheduler.step()

        logger.info(
            f"Epoch {epoch+1}/{args.epochs} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.4f} Cause: {train_cause_acc:.4f} | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.4f} F1: {val_metrics['f1']:.4f} "
            f"River: {val_metrics['river_acc']:.4f} Trash: {val_metrics['trash_acc']:.4f} | "
            f"TP:{val_metrics['tp']} FP:{val_metrics['fp']} FN:{val_metrics['fn']} TN:{val_metrics['tn']}"
        )

        save = False
        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
            save = True
        if val_cause_acc > best_cause_acc:
            best_cause_acc = val_cause_acc
            save = True

        if save:
            checkpoint = {
                "model_state_dict": model.state_dict(),
                "backbone": args.backbone,
                "num_classes": 2,
                "num_causes": 2,
                "val_acc": val_acc,
                "val_f1": val_metrics["f1"],
                "val_cause_acc": val_cause_acc,
                "val_river_acc": val_metrics["river_acc"],
                "val_trash_acc": val_metrics["trash_acc"],
                "val_depth_mae": val_depth_mae,
                "epoch": epoch + 1,
                "train_args": vars(args),
            }
            torch.save(checkpoint, CHECKPOINT_DIR / "best.pt")
            logger.info(f"Saved best model (F1={val_metrics['f1']:.4f}, Cause={val_cause_acc:.4f})")

        early_stopping(val_loss)
        if early_stopping.should_stop:
            logger.info(f"Early stopping at epoch {epoch+1}")
            break

    logger.info(f"\n{'='*60}")
    logger.info(f"TRAINING COMPLETE")
    logger.info(f"Best Val F1: {best_val_f1:.4f}")
    logger.info(f"Best Cause Acc: {best_cause_acc:.4f}")
    logger.info(f"{'='*60}")

    logger.info(f"\nRunning final evaluation on test set...")
    test_loss, test_acc, test_depth_mae, test_cause_acc, test_metrics = evaluate(
        model, test_loader, criterion_cls, criterion_depth, criterion_cause, device
    )

    logger.info(f"{'='*60}")
    logger.info(f"TEST SET RESULTS")
    logger.info(f"{'='*60}")
    logger.info(f"Test Acc: {test_acc:.4f}")
    logger.info(f"Test F1: {test_metrics['f1']:.4f}")
    logger.info(f"Test Precision: {test_metrics['precision']:.4f}")
    logger.info(f"Test Recall: {test_metrics['recall']:.4f}")
    logger.info(f"Test Cause Acc: {test_cause_acc:.4f}")
    logger.info(f"Test River Acc: {test_metrics['river_acc']:.4f}")
    logger.info(f"Test Trash Acc: {test_metrics['trash_acc']:.4f}")
    logger.info(f"Test Depth MAE: {test_depth_mae:.2f}cm")
    logger.info(f"TP:{test_metrics['tp']} FP:{test_metrics['fp']} FN:{test_metrics['fn']} TN:{test_metrics['tn']}")
    logger.info(f"{'='*60}")

    results = {
        "best_val_f1": best_val_f1,
        "best_cause_acc": best_cause_acc,
        "test_acc": test_acc,
        "test_f1": test_metrics["f1"],
        "test_precision": test_metrics["precision"],
        "test_recall": test_metrics["recall"],
        "test_cause_acc": test_cause_acc,
        "test_river_acc": test_metrics["river_acc"],
        "test_trash_acc": test_metrics["trash_acc"],
        "test_depth_mae": test_depth_mae,
        "test_tp": test_metrics["tp"],
        "test_fp": test_metrics["fp"],
        "test_fn": test_metrics["fn"],
        "test_tn": test_metrics["tn"],
    }

    results_path = CHECKPOINT_DIR / "training_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Results saved to {results_path}")


if __name__ == "__main__":
    main()
