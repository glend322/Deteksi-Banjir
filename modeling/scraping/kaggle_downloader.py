"""
Kaggle Flood Image Downloader

Downloads flood detection datasets from Kaggle.
Requires: KAGGLE_USERNAME and KAGGLE_KEY in .env or environment.

Usage:
  python kaggle_downloader.py
"""
import os
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from utils import log


# Known flood datasets on Kaggle
DATASETS = [
    {
        "slug": "ritvik1909/flood-detection",
        "description": "Flood detection images with annotations",
    },
    {
        "slug": "anshitagarwal/flood-image-dataset",
        "description": "Flood vs non-flood image classification",
    },
    {
        "slug": "社恐的咕咕/ Flood Image",
        "description": "Flood severity images",
    },
]


def check_kaggle_cli() -> bool:
    try:
        result = subprocess.run(
            ["kaggle", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def install_kaggle():
    log("Installing kaggle CLI...")
    subprocess.run([sys.executable, "-m", "pip", "install", "kaggle"], check=True)


def setup_kaggle_credentials():
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(exist_ok=True)
    cred_file = kaggle_dir / "kaggle.json"

    username = os.environ.get("KAGGLE_USERNAME", "")
    key = os.environ.get("KAGGLE_KEY", "")

    if not username or not key:
        log("WARNING: KAGGLE_USERNAME or KAGGLE_KEY not set.")
        log("Set them in .env or environment variables.")
        log("Alternatively, download datasets manually from Kaggle.")
        return False

    if not cred_file.exists():
        import json
        with open(cred_file, "w") as f:
            json.dump({"username": username, "key": key}, f)
        log("Kaggle credentials saved.")
    return True


def download_dataset(slug: str, dest_dir: str) -> bool:
    log(f"  Downloading: {slug}")
    try:
        subprocess.run(
            ["kaggle", "datasets", "download", "-d", slug, "-p", dest_dir, "--unzip"],
            check=True,
            timeout=300,
        )
        return True
    except subprocess.CalledProcessError as e:
        log(f"  Failed to download {slug}: {e}")
        return False


def main():
    output_dir = Path(__file__).parent.parent / "data" / "raw" / "kaggle"
    output_dir.mkdir(parents=True, exist_ok=True)

    if not check_kaggle_cli():
        install_kaggle()

    has_creds = setup_kaggle_credentials()

    if not has_creds:
        log("\nCannot download from Kaggle without credentials.")
        log("Manual download instructions:")
        log("  1. Go to https://www.kaggle.com/datasets")
        log("  2. Search for 'flood detection' or 'flood image'")
        log("  3. Download and extract to: data/raw/kaggle/")
        log("\nRecommended datasets:")
        for ds in DATASETS:
            log(f"  - {ds['slug']}: {ds['description']}")
        return

    for ds in DATASETS:
        download_dataset(ds["slug"], str(output_dir / ds["slug"].split("/")[-1]))

    log("Kaggle download complete!")


if __name__ == "__main__":
    main()
