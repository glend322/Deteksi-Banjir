"""
CCTV Client — Scraping CCTV Pantau Semarang

Scrapes CCTV data from pantausemar.semarangkota.go.id and extracts frames
from HLS live streams for flood detection analysis.

Source: Pemkot Semarang via Pantau Semar platform
Stream: HLS (HTTP Live Streaming) via livepantau.semarangkota.go.id
"""
import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

PANTAUSEMAR_URL = "https://pantausemar.semarangkota.go.id/"

CCTV_CATEGORIES = {
    "rawan_genangan": "df69dbea-87c9-4d79-9ddc-f388c33f2dc9",
    "sungai": "194fd5d9-098f-4dbe-93da-8288c6761bf0",
    "pompa_air": "5b5b7e51-3a2e-446f-8fae-50d8e9e7196d",
    "lalin": "fc3ed271-787c-4191-a7dd-fc84314a9f71",
}

FLOOD_CATEGORIES = ["rawan_genangan", "sungai", "pompa_air"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
}


@dataclass
class CCTVStream:
    cctv_id: int
    name: str
    owner: str
    lat: float
    lng: float
    stream_url: str
    link_id: int
    status: int = 1
    category: str = ""


@dataclass
class CCTVScanResult:
    timestamp: float
    total_cameras: int
    scanned_cameras: int = 0
    successful_frames: int = 0
    failed_frames: int = 0
    flood_detections: list = field(default_factory=list)
    errors: list = field(default_factory=list)


class CCTVClient:
    """
    Client for accessing Pantau Semar CCTV streams.

    Workflow:
    1. Scrape HTML to get list of CCTV cameras + HLS stream URLs
    2. Filter by flood-relevant categories
    3. Extract frames from HLS streams using ffmpeg
    """

    def __init__(
        self,
        categories: list[str] | None = None,
        cache_dir: str | Path = "cache/cctv",
        request_timeout: float = 15.0,
    ):
        self.categories = categories or FLOOD_CATEGORIES
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.request_timeout = request_timeout
        self._cameras: list[CCTVStream] = []
        self._last_fetch: float = 0
        self._fetch_interval: float = 300

    async def get_cameras(self, force_refresh: bool = False) -> list[CCTVStream]:
        now = time.time()
        if not force_refresh and self._cameras and (now - self._last_fetch) < self._fetch_interval:
            return self._cameras

        all_cameras = []
        for cat_name in self.categories:
            cat_uuid = CCTV_CATEGORIES.get(cat_name)
            if not cat_uuid:
                continue
            cameras = await self._scrape_cameras(cat_uuid, cat_name)
            all_cameras.extend(cameras)

        seen = set()
        unique = []
        for cam in all_cameras:
            key = (cam.cctv_id, cam.link_id)
            if key not in seen:
                seen.add(key)
                unique.append(cam)

        self._cameras = unique
        self._last_fetch = now
        logger.info(f"[CCTV] Fetched {len(unique)} cameras across {len(self.categories)} categories")
        return unique

    async def _scrape_cameras(self, category_uuid: str, category_name: str) -> list[CCTVStream]:
        url = f"{PANTAUSEMAR_URL}?cctv_category_id={category_uuid}"
        cameras = []

        try:
            async with httpx.AsyncClient(timeout=self.request_timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=HEADERS)
                resp.raise_for_status()
                html = resp.text

            match = re.search(r"var\s+cctvs\s*=\s*(\[.*?\])\s*;", html, re.DOTALL)
            if not match:
                logger.warning(f"[CCTV] No cctvs variable found for category {category_name}")
                return cameras

            cctv_data = json.loads(match.group(1))

            for cctv in cctv_data:
                cctv_id = cctv.get("cctv_id", 0)
                name = cctv.get("owner_name", "Unknown")
                lat = float(cctv.get("lat", 0))
                lng = float(cctv.get("lng", 0))

                for link in cctv.get("links", []):
                    if link.get("status") != 1:
                        continue
                    stream_url = link.get("url", "")
                    if not stream_url or not stream_url.endswith(".m3u8"):
                        continue

                    cameras.append(CCTVStream(
                        cctv_id=cctv_id,
                        name=link.get("name", name),
                        owner=link.get("owner_name", ""),
                        lat=lat,
                        lng=lng,
                        stream_url=stream_url,
                        link_id=link.get("id", 0),
                        status=link.get("status", 1),
                        category=category_name,
                    ))

        except httpx.HTTPError as e:
            logger.error(f"[CCTV] HTTP error scraping {category_name}: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"[CCTV] JSON parse error for {category_name}: {e}")
        except Exception as e:
            logger.error(f"[CCTV] Unexpected error for {category_name}: {e}")

        return cameras

    async def extract_frame(self, camera: CCTVStream) -> Optional[bytes]:
        frame = await self._extract_frame_ffmpeg(camera.stream_url)
        if frame:
            return frame
        frame = await self._extract_frame_http(camera.stream_url)
        return frame

    def _get_ffmpeg_path(self) -> str:
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            pass
        return "ffmpeg"

    async def _extract_frame_ffmpeg(self, m3u8_url: str) -> Optional[bytes]:
        try:
            import subprocess
            import tempfile

            ffmpeg_path = self._get_ffmpeg_path()

            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name

            cmd = [
                ffmpeg_path, "-y",
                "-i", m3u8_url,
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

        except (FileNotFoundError, asyncio.TimeoutError, Exception):
            return None

    async def _extract_frame_http(self, m3u8_url: str) -> Optional[bytes]:
        try:
            async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                resp = await client.get(m3u8_url, headers=HEADERS)
                resp.raise_for_status()
                content = resp.text

                ts_urls = re.findall(r'(https?://[^\s"\']+\.ts[^\s"\']*)', content)
                if not ts_urls:
                    base_url = m3u8_url.rsplit("/", 1)[0] + "/"
                    ts_urls = [
                        base_url + line.strip()
                        for line in content.split("\n")
                        if line.strip() and not line.startswith("#") and line.strip().endswith(".ts")
                    ]

                if not ts_urls:
                    return None

                ts_resp = await client.get(ts_urls[0], headers=HEADERS)
                ts_resp.raise_for_status()

                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".ts", delete=False) as tmp_ts:
                    tmp_ts.write(ts_resp.content)
                    ts_path = tmp_ts.name

                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_jpg:
                    jpg_path = tmp_jpg.name

                ffmpeg_path = self._get_ffmpeg_path()
                cmd = [
                    ffmpeg_path, "-y",
                    "-i", ts_path,
                    "-frames:v", "1",
                    "-q:v", "2",
                    jpg_path,
                ]

                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await asyncio.wait_for(proc.communicate(), timeout=10)

                frame = None
                if proc.returncode == 0 and Path(jpg_path).exists():
                    frame = Path(jpg_path).read_bytes()

                Path(ts_path).unlink(missing_ok=True)
                Path(jpg_path).unlink(missing_ok=True)
                return frame

        except Exception as e:
            logger.debug(f"[CCTV] HTTP frame extraction failed: {e}")
            return None

    async def scan_all_cameras(self) -> tuple[CCTVScanResult, list[tuple[CCTVStream, bytes]]]:
        cameras = await self.get_cameras()
        result = CCTVScanResult(
            timestamp=time.time(),
            total_cameras=len(cameras),
        )

        semaphore = asyncio.Semaphore(5)

        async def _scan_one(cam: CCTVStream):
            async with semaphore:
                result.scanned_cameras += 1
                frame = await self.extract_frame(cam)
                if frame:
                    result.successful_frames += 1
                    return (cam, frame)
                else:
                    result.failed_frames += 1
                    return None

        tasks = [_scan_one(cam) for cam in cameras]
        scan_results = await asyncio.gather(*tasks, return_exceptions=True)

        frames = []
        for r in scan_results:
            if isinstance(r, tuple):
                cam, frame = r
                frames.append((cam, frame))

        return result, frames
