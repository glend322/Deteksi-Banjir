"""
Data Scraper Utilities — Rate Limiter, Cache, Retry

Shared utilities for all scraping modules.
"""
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent.parent / "data" / "raw"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def get_cached(url: str, max_age_hours: int = 24) -> Optional[str]:
    key = cache_key(url)
    cache_file = CACHE_DIR / f"{key}.json"

    if cache_file.exists():
        age = time.time() - cache_file.stat().st_mtime
        if age < max_age_hours * 3600:
            return cache_file.read_text(encoding="utf-8")

    return None


def set_cached(url: str, content: str):
    key = cache_key(url)
    cache_file = CACHE_DIR / f"{key}.json"
    cache_file.write_text(content, encoding="utf-8")


class RateLimiter:
    def __init__(self, requests_per_second: float = 1.0):
        self.min_interval = 1.0 / requests_per_second
        self._last_request = 0.0

    def wait(self):
        now = time.time()
        elapsed = now - self._last_request
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_request = time.time()


async def fetch_with_retry(
    url: str,
    max_retries: int = 3,
    timeout: float = 30.0,
    headers: dict | None = None,
    use_cache: bool = True,
    cache_max_age_hours: int = 24,
) -> Optional[str]:
    if use_cache:
        cached = get_cached(url, cache_max_age_hours)
        if cached:
            logger.debug(f"[Cache hit] {url}")
            return cached

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=headers or {})
                resp.raise_for_status()
                content = resp.text

                if use_cache:
                    set_cached(url, content)

                return content

        except httpx.HTTPStatusError as e:
            logger.warning(f"[HTTP {e.response.status_code}] {url} (attempt {attempt + 1})")
            if e.response.status_code == 429:
                time.sleep(5 * (attempt + 1))
            elif e.response.status_code >= 500:
                time.sleep(2 * (attempt + 1))
            else:
                return None

        except httpx.HTTPError as e:
            logger.warning(f"[HTTP Error] {url}: {e} (attempt {attempt + 1})")
            time.sleep(2 * (attempt + 1))

        except Exception as e:
            logger.error(f"[Error] {url}: {e}")
            return None

    logger.error(f"[Failed after {max_retries} retries] {url}")
    return None
