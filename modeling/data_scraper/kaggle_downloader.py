"""
Kaggle Downloader — Flood Image Datasets

Downloads flood detection datasets from Kaggle for CV model training.
Requires: KAGGLE_USERNAME and KAGGLE_KEY in .env
"""
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
DATA_DIR.mkdir(parents=True, exist_ok=True)

FLOOD_DATASETS = [
    "naiyakhalid/flood-prediction-dataset",
]


def download_dataset(dataset: str, force: bool = False) -> bool:
    api_key = os.environ.get("KAGGLE_USERNAME")
    api_secret = os.environ.get("KAGGLE_KEY")

    if not api_key or not api_secret:
        logger.warning("[Kaggle] KAGGLE_USERNAME or KAGGLE_KEY not set in .env")
        logger.info("[Kaggle] Download manually from:")
        for ds in FLOOD_DATASETS:
            logger.info(f"  https://www.kaggle.com/datasets/{ds}")
        return False

    output_dir = DATA_DIR / dataset.replace("/", "_")

    if output_dir.exists() and not force:
        logger.info(f"[Kaggle] Dataset already exists: {output_dir}")
        return True

    try:
        cmd = [
            "kaggle", "datasets", "download",
            "-d", dataset,
            "-p", str(output_dir),
            "--unzip",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode == 0:
            logger.info(f"[Kaggle] Downloaded {dataset} to {output_dir}")
            return True
        else:
            logger.error(f"[Kaggle] Download failed: {result.stderr}")
            return False

    except FileNotFoundError:
        logger.error("[Kaggle] kaggle CLI not found. Install with: pip install kaggle")
        return False
    except subprocess.TimeoutExpired:
        logger.error("[Kaggle] Download timed out")
        return False


def download_all(force: bool = False) -> dict[str, bool]:
    results = {}
    for dataset in FLOOD_DATASETS:
        results[dataset] = download_dataset(dataset, force=force)
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = download_all()
    for ds, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {ds}: {status}")
