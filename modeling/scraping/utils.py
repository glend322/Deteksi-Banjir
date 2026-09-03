import os
import time
import hashlib
import json
import requests
from pathlib import Path
from functools import wraps
from datetime import datetime


# Semarang bounding box
SEMARANG_BOUNDS = {
    "lat_min": -7.05,
    "lat_max": -6.85,
    "lng_min": 110.35,
    "lng_max": 110.55,
}

SEMARANG_CENTER = {"lat": -6.968, "lng": 110.435}


class RateLimiter:
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_call = 0.0

    def wait(self):
        elapsed = time.time() - self.last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_call = time.time()


class Cache:
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key(self, url: str) -> str:
        return hashlib.md5(url.encode()).hexdigest()

    def get(self, url: str) -> dict | None:
        path = self.cache_dir / f"{self._key(url)}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def set(self, url: str, data: dict):
        path = self.cache_dir / f"{self._key(url)}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_raw(self, key: str) -> dict | None:
        path = self.cache_dir / f"{key}.json"
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def set_raw(self, key: str, data: dict):
        path = self.cache_dir / f"{key}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def fetch_with_retry(
    url: str,
    rate_limiter: RateLimiter | None = None,
    cache: Cache | None = None,
    max_retries: int = 3,
    timeout: int = 30,
    params: dict | None = None,
    headers: dict | None = None,
) -> dict | None:
    if cache:
        cached = cache.get(url)
        if cached:
            return cached

    for attempt in range(max_retries):
        if rate_limiter:
            rate_limiter.wait()
        try:
            resp = requests.get(url, timeout=timeout, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json() if "json" in resp.headers.get("content-type", "") else resp.text
            if cache and isinstance(data, dict):
                cache.set(url, data)
            return data
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return None


def download_file(
    url: str,
    dest: str,
    rate_limiter: RateLimiter | None = None,
    max_retries: int = 3,
    timeout: int = 60,
) -> bool:
    dest_path = Path(dest)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        print(f"  Already exists: {dest}")
        return True

    for attempt in range(max_retries):
        if rate_limiter:
            rate_limiter.wait()
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"  Downloaded: {dest}")
            return True
        except Exception as e:
            print(f"  Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    return False


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")
