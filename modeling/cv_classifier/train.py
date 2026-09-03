"""
CV Flood Image Classifier - Training

Trains a dual-head ResNet50:
  - Classification: flood severity (4 classes)
  - Regression: water depth (cm)

Features:
  - Mixed-precision training (AMP)
  - Cosine annealing LR schedule
  - Class-balanced sampling
  - Early stopping
  - Checkpoint saving (best + last)
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.amp import autocast, GradScaler

sys.path.insert(0, str(Path(__file__).parent))
from model import FloodClassifier, SEVERITY_CLASSES
from dataset import prepare_dataloaders

CHECKPOINT_DIR = Path(__file__).parent / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


def compute_class_weights(samples: list[dict], num_classes: int = 4) -> torch.Tensor:
    counts = np.zeros(num_classes)
    for s in samples:
        counts[s["label_idx"]] += 1
    weights = 1.0 / (counts + 1e-6)
    weights = weights / weights.sum() * num_classes
    return torch.FloatTensor(weights)


def train_one_epoch(model, loader, optimizer, cls_weight, dep_weight, device, scaler, use_amp=False):
    model.train()
    total_cls_loss = 0
    total_dep_loss = 0
    total_loss = 0
    correct = 0
    total = 0

    for imgs, targets in loader:
        imgs = imgs.to(device, non_blocking=True)
        labels = targets["label"].to(device, non_blocking=True)
        depths = targets["depth_cm"].to(device, non_blocking=True).float()

        optimizer.zero_grad(set_to_none=True)

        with autocast(device_type=device.type, enabled=use_amp):
            out = model(imgs)
            cls_loss = nn.functional.cross_entropy(out["logits"], labels)
            dep_loss = nn.functional.mse_loss(out["depth_cm"], depths)
            loss = cls_weight * cls_loss + dep_weight * dep_loss

        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        scaler.step(optimizer)
        scaler.update()

        total_cls_loss += cls_loss.item() * imgs.size(0)
        total_dep_loss += dep_loss.item() * imgs.size(0)
        total_loss += loss.item() * imgs.size(0)

        preds = out["logits"].argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += imgs.size(0)

    n = len(loader.dataset)
    return {
        "cls_loss": total_cls_loss / n,
        "dep_loss": total_dep_loss / n,
        "loss": total_loss / n,
        "accuracy": correct / total,
    }


@torch.no_grad()
def validate(model, loader, cls_weight, dep_weight, device):
    model.eval()
    total_cls_loss = 0
    total_dep_loss = 0
    total_loss = 0
    correct = 0
    total = 0
    all_preds = []
    all_labels = []

    for imgs, targets in loader:
        imgs = imgs.to(device, non_blocking=True)
        labels = targets["label"].to(device, non_blocking=True)
        depths = targets["depth_cm"].to(device, non_blocking=True).float()

        out = model(imgs)
        cls_loss = nn.functional.cross_entropy(out["logits"], labels)
        dep_loss = nn.functional.mse_loss(out["depth_cm"], depths)
        loss = cls_weight * cls_loss + dep_weight * dep_loss

        total_cls_loss += cls_loss.item() * imgs.size(0)
        total_dep_loss += dep_loss.item() * imgs.size(0)
        total_loss += loss.item() * imgs.size(0)

        preds = out["logits"].argmax(dim=1)
        correct += (preds == labels).sum().item()
        total += imgs.size(0)

        all_preds.extend(preds.cpu().numpy())
        all_labels.extend(labels.cpu().numpy())

    n = len(loader.dataset)
    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    per_class_acc = {}
    for i, cls in enumerate(SEVERITY_CLASSES):
        mask = all_labels == i
        if mask.sum() > 0:
            per_class_acc[cls] = float((all_preds[mask] == i).mean())
        else:
            per_class_acc[cls] = 0.0

    return {
        "cls_loss": total_cls_loss / n,
        "dep_loss": total_dep_loss / n,
        "loss": total_loss / n,
        "accuracy": correct / total,
        "per_class_acc": per_class_acc,
    }


def main():
    parser = argparse.ArgumentParser(description="Train CV flood classifier")
    parser.add_argument("--data-dir", type=str, default=None, help="Image data directory")
    parser.add_argument("--backbone", type=str, default="mobilenet_v3_small", choices=["resnet50", "efficientnet_b0", "mobilenet_v3_small"])
    parser.add_argument("--config", type=str, default="config.yaml", help="Config file")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--image-size", type=int, default=224)
    parser.add_argument("--patience", type=int, default=10, help="Early stopping patience")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # Data
    loaders = prepare_dataloaders(
        data_dir=args.data_dir,
        image_size=args.image_size,
        batch_size=args.batch_size,
        augment=True,
    )

    # Model
    model = FloodClassifier(num_classes=4, pretrained=True, backbone=args.backbone).to(device)
    print(f"Parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Class weights
    cls_weights = compute_class_weights(loaders["train_samples"]).to(device)
    print(f"Class weights: {dict(zip(SEVERITY_CLASSES, cls_weights.tolist()))}")

    # Loss weights from config
    cls_w = 0.5
    dep_w = 0.5

    # Optimizer + scheduler
    optimizer = AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)

    use_amp = device.type == "cuda"
    scaler = GradScaler(enabled=use_amp)

    best_val_acc = 0
    patience_counter = 0
    history = []

    print(f"\nStarting training for {args.epochs} epochs...")
    print("=" * 60)

    for epoch in range(1, args.epochs + 1):
        t0 = time.time()

        train_metrics = train_one_epoch(model, loaders["train"], optimizer, cls_w, dep_w, device, scaler, use_amp)
        val_metrics = validate(model, loaders["val"], cls_w, dep_w, device)
        scheduler.step()

        elapsed = time.time() - t0
        lr = optimizer.param_groups[0]["lr"]

        print(
            f"Epoch {epoch:3d}/{args.epochs} | "
            f"train_loss={train_metrics['loss']:.4f} acc={train_metrics['accuracy']:.4f} | "
            f"val_loss={val_metrics['loss']:.4f} acc={val_metrics['accuracy']:.4f} | "
            f"lr={lr:.6f} | {elapsed:.1f}s"
        )

        history.append({
            "epoch": epoch,
            "train_loss": train_metrics["loss"],
            "train_acc": train_metrics["accuracy"],
            "val_loss": val_metrics["loss"],
            "val_acc": val_metrics["accuracy"],
            "lr": lr,
        })

        # Save best
        if val_metrics["accuracy"] > best_val_acc:
            best_val_acc = val_metrics["accuracy"]
            patience_counter = 0
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": val_metrics["accuracy"],
                "val_loss": val_metrics["loss"],
                "backbone": args.backbone,
            }, CHECKPOINT_DIR / "best.pt")
            print(f"  -> New best (val_acc={best_val_acc:.4f}), saved best.pt")
        else:
            patience_counter += 1

        # Save last
        torch.save({
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "val_acc": val_metrics["accuracy"],
        }, CHECKPOINT_DIR / "last.pt")

        if patience_counter >= args.patience:
            print(f"\nEarly stopping at epoch {epoch} (patience={args.patience})")
            break

    # Save metadata
    meta = {
        "epochs_trained": epoch,
        "best_val_acc": best_val_acc,
        "device": str(device),
        "backbone": args.backbone,
        "class_weights": cls_weights.tolist(),
        "severity_classes": SEVERITY_CLASSES,
    }
    with open(CHECKPOINT_DIR / "train_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    with open(CHECKPOINT_DIR / "train_history.json", "w") as f:
        json.dump(history, f, indent=2)

    print(f"\nTraining complete. Best val_acc: {best_val_acc:.4f}")
    print(f"Checkpoints saved to {CHECKPOINT_DIR}")


if __name__ == "__main__":
    main()
