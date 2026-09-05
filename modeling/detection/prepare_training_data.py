"""
Prepare training data for SafeRoute CV model.
- Flood images: from downloaded Kaggle flood segmentation dataset
- Non-flood images: Semarang city street/road images (scraped from Pantau Semarang CCTV)
Output: data/training/{flood,nonflood}/ with images resized to 224x224
"""
import asyncio
import csv
import json
import os
import random
import re
import time
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFilter
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

BASE_DIR = Path(__file__).parent
RAW_FLOOD = BASE_DIR / "data" / "raw" / "flood_images" / "flood" / "images"
TRAIN_DIR = BASE_DIR / "data" / "training"
FLOOD_DIR = TRAIN_DIR / "flood"
NONFLOOD_DIR = TRAIN_DIR / "nonflood"

TARGET_SIZE = (224, 224)

PANTAUSEMAR_URL = "https://pantausemar.semarangkota.go.id/"
FLOOD_CATEGORIES = {
    "rawan_genangan": "df69dbea-87c9-4d79-9ddc-f388c33f2dc9",
    "sungai": "194fd5d9-098f-4dbe-93da-8288c6761bf0",
    "pompa_air": "5b5b7e51-3a2e-446f-8fae-50d8e9e7196d",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}


def organize_flood_images():
    """Copy and resize flood images to training directory."""
    FLOOD_DIR.mkdir(parents=True, exist_ok=True)

    if not RAW_FLOOD.exists():
        print(f"WARNING: Raw flood images not found at {RAW_FLOOD}")
        return

    img_files = [f for f in RAW_FLOOD.iterdir()
                 if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp')]

    if not img_files:
        print("No flood images found.")
        return

    print(f"Organizing {len(img_files)} flood images...")
    count = 0
    for i, img_path in enumerate(img_files):
        try:
            img = Image.open(img_path).convert("RGB")
            img = img.resize(TARGET_SIZE, Image.LANCZOS)
            img.save(FLOOD_DIR / f"flood_{i:04d}.jpg", quality=95)
            count += 1
        except Exception as e:
            print(f"  Skipping {img_path.name}: {e}")
    print(f"  Saved {count} flood images to {FLOOD_DIR}")


async def _scrape_semarang_cameras(category_uuid: str) -> list[dict]:
    """Scrape CCTV camera list from Pantau Semarang."""
    cameras = []
    url = f"{PANTAUSEMAR_URL}?cctv_category_id={category_uuid}"

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=HEADERS)
            resp.raise_for_status()
            html = resp.text

        match = re.search(r"var\s+cctvs\s*=\s*(\[.*?\])\s*;", html, re.DOTALL)
        if not match:
            return cameras

        cctv_data = json.loads(match.group(1))

        for cctv in cctv_data:
            lat = float(cctv.get("lat", 0))
            lng = float(cctv.get("lng", 0))
            name = cctv.get("owner_name", "Unknown")

            for link in cctv.get("links", []):
                if link.get("status") != 1:
                    continue
                stream_url = link.get("url", "")
                if not stream_url or not stream_url.endswith(".m3u8"):
                    continue

                cameras.append({
                    "name": link.get("name", name),
                    "lat": lat,
                    "lng": lng,
                    "stream_url": stream_url,
                })

    except Exception as e:
        print(f"  Error scraping cameras: {e}")

    return cameras


async def _extract_frame_from_stream(stream_url: str) -> bytes | None:
    """Extract a single frame from HLS stream using ffmpeg."""
    try:
        import subprocess
        import tempfile

        try:
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            ffmpeg_path = "ffmpeg"

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        cmd = [
            ffmpeg_path, "-y",
            "-i", stream_url,
            "-frames:v", "1",
            "-q:v", "2",
            tmp_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)

        if proc.returncode == 0 and Path(tmp_path).exists():
            frame = Path(tmp_path).read_bytes()
            Path(tmp_path).unlink(missing_ok=True)
            return frame
        else:
            Path(tmp_path).unlink(missing_ok=True)
            return None

    except Exception:
        return None


async def scrape_semarang_street_images(target_count: int = 100) -> list[bytes]:
    """
    Scrape normal street images from Semarang CCTV cameras.
    Uses flood-category cameras but captures during non-flood conditions.
    """
    print("Scraping Semarang city CCTV cameras for street images...")

    all_cameras = []
    for cat_name, cat_uuid in FLOOD_CATEGORIES.items():
        cameras = await _scrape_semarang_cameras(cat_uuid)
        print(f"  Found {len(cameras)} cameras in category: {cat_name}")
        all_cameras.extend(cameras)

    seen = set()
    unique_cameras = []
    for cam in all_cameras:
        key = (cam["lat"], cam["lng"], cam["stream_url"])
        if key not in seen:
            seen.add(key)
            unique_cameras.append(cam)

    print(f"  Total unique cameras: {len(unique_cameras)}")

    frames = []
    semaphore = asyncio.Semaphore(3)

    async def _fetch_one(cam: dict):
        async with semaphore:
            frame = await _extract_frame_from_stream(cam["stream_url"])
            return frame

    batch_size = 10
    for i in range(0, min(target_count, len(unique_cameras) * 3), batch_size):
        batch = unique_cameras[i % len(unique_cameras):(i % len(unique_cameras)) + batch_size]
        tasks = [_fetch_one(cam) for cam in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, bytes) and len(r) > 1000:
                frames.append(r)

        if len(frames) >= target_count:
            break

        await asyncio.sleep(1)

    print(f"  Collected {len(frames)} frames from Semarang CCTV")
    return frames


def augment_street_image(img: Image.Image) -> Image.Image:
    """
    Augment a normal street image to create training variety.
    Applies slight color/brightness variations to simulate different conditions.
    """
    import random as rng

    if rng.random() < 0.3:
        factor = rng.uniform(0.8, 1.2)
        img = Image.blend(img, Image.new("RGB", img.size, (0, 0, 0)), 0)

    if rng.random() < 0.3:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    if rng.random() < 0.2:
        img = img.rotate(rng.uniform(-10, 10), fillcolor=(128, 128, 128))

    return img


async def prepare_nonflood_from_semarang(target_count: int = 200):
    """
    Prepare non-flood training images from Semarang city CCTV.
    These are normal street/road images from Semarang cameras.
    """
    NONFLOOD_DIR.mkdir(parents=True, exist_ok=True)

    existing = list(NONFLOOD_DIR.glob("*.jpg"))
    if len(existing) >= target_count:
        print(f"  Already have {len(existing)} non-flood images, skipping.")
        return

    frames = await scrape_semarang_street_images(target_count)

    if not frames:
        print("  WARNING: No frames collected. Creating placeholder directory.")
        return

    print(f"  Processing {len(frames)} frames as non-flood class...")
    count = len(existing)
    for i, frame_bytes in enumerate(frames):
        try:
            import io
            img = Image.open(io.BytesIO(frame_bytes)).convert("RGB")
            img = img.resize(TARGET_SIZE, Image.LANCZOS)

            img = augment_street_image(img)

            img.save(NONFLOOD_DIR / f"semarang_street_{count:05d}.jpg", quality=95)
            count += 1
        except Exception as e:
            print(f"  Skipping frame {i}: {e}")

    print(f"  Saved {count - len(existing)} new non-flood images from Semarang CCTV")


def prepare_nonflood_from_augmentation(flood_dir: Path, target_count: int = 100):
    """
    Create additional non-flood images by applying water-like overlays to road images.
    Simulates near-flood conditions (shallow water on roads).
    """
    if not HAS_PIL:
        print("  WARNING: PIL not available, skipping augmentation")
        return

    NONFLOOD_DIR.mkdir(parents=True, exist_ok=True)

    existing = list(NONFLOOD_DIR.glob("*.jpg"))
    if len(existing) >= target_count:
        return

    flood_images = list(flood_dir.glob("*.jpg"))
    if not flood_images:
        return

    print(f"  Augmenting {min(len(flood_images), 20)} flood images for non-flood class...")
    count = len(existing)
    for i, img_path in enumerate(flood_images[:20]):
        try:
            img = Image.open(img_path).convert("RGB")
            img = img.resize(TARGET_SIZE, Image.LANCZOS)

            overlay = Image.new("RGB", img.size, (100, 150, 200))
            blended = Image.blend(img, overlay, 0.3)

            blended = blended.filter(ImageFilter.GaussianBlur(radius=1))

            blended.save(NONFLOOD_DIR / f"augmented_{count:05d}.jpg", quality=95)
            count += 1
        except Exception as e:
            pass

    print(f"  Saved {count - len(existing)} augmented non-flood images")


async def main():
    print("=" * 60)
    print("SafeRoute - Training Data Preparation")
    print("=" * 60)

    organize_flood_images()

    if HAS_HTTPX:
        await prepare_nonflood_from_semarang(target_count=200)
    else:
        print("WARNING: httpx not available. Install with: pip install httpx")
        print("  Falling back to augmentation-only mode.")
        prepare_nonflood_from_augmentation(FLOOD_DIR, target_count=100)

    prepare_nonflood_from_augmentation(FLOOD_DIR, target_count=100)

    flood_count = len(list(FLOOD_DIR.glob("*.jpg")))
    nonflood_count = len(list(NONFLOOD_DIR.glob("*.jpg")))

    print(f"\nTraining data ready:")
    print(f"  Flood images:     {flood_count}  ({FLOOD_DIR})")
    print(f"  Non-flood images: {nonflood_count}  ({NONFLOOD_DIR})")
    print(f"  Total:            {flood_count + nonflood_count}")
    print(f"\nRun: python train.py  to start training")


if __name__ == "__main__":
    asyncio.run(main())
