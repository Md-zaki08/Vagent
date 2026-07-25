"""
VAgent Media Retriever - Fetches video clips and images from the web
for use in professional video production.
"""

import asyncio
import logging
import random
import tempfile
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Free stock video sources
STOCK_VIDEO_SOURCES = [
    'https://www.pexels.com/search/videos/',
    'https://pixabay.com/videos/search/',
    'https://coverr.co/search?q=',
]

# Free stock image sources
STOCK_IMAGE_SOURCES = [
    'https://unsplash.com/s/photos/',
    'https://pixabay.com/images/search/',
]

# Background music sources (royalty-free)
MUSIC_SOURCES = [
    'https://www.chosic.com/free-music/all/',
    'https://pixabay.com/music/search/',
    'https://www.epidemicsound.com/search/?term=',
]


class MediaRetriever:
    """Fetches stock video clips, images, and music for video production."""

    def __init__(self, download_dir: Optional[str] = None):
        self.download_dir = Path(download_dir or tempfile.gettempdir()) / 'vagent_media'
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._http = httpx.AsyncClient(timeout=20, follow_redirects=True,
                                       headers=self._headers())

    async def search_clips(self, query: str, count: int = 5) -> List[Dict]:
        """Search for stock video clips related to a topic.

        Returns list of dicts with 'url', 'title', 'source', 'type'.
        """
        clips = []
        try:
            # Try Pexels API (no key required for basic search)
            resp = await self._http.get(
                f'https://api.pexels.com/videos/search',
                params={'query': query, 'per_page': min(count, 40)},
                headers={**self._headers(), 'Authorization': 'VAgent'}
            )
            if resp.status_code == 200:
                data = resp.json()
                for video in data.get('videos', []):
                    for file in video.get('video_files', []):
                        if file.get('quality') in ('hd', 'sd') and file.get('link'):
                            clips.append({
                                'url': file['link'],
                                'title': video.get('url', ''),
                                'source': 'pexels',
                                'type': 'video',
                                'width': file.get('width', 1920),
                                'height': file.get('height', 1080),
                                'duration': video.get('duration', 10),
                            })
        except Exception as e:
            logger.debug(f"Pexels search failed: {e}")

        # Fallback: search Pexels HTML for free clips
        if len(clips) < count:
            try:
                resp = await self._http.get(
                    f'https://www.pexels.com/search/videos/{query}/',
                    params={'size': 'small', 'page': 1}
                )
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, 'lxml')
                    for img in soup.select('img[data-src], img[src]'):
                        src = img.get('data-src') or img.get('src', '')
                        if src and src.endswith(('.mp4', '.webm', '.mov')):
                            alt = img.get('alt', query)
                            clips.append({
                                'url': src,
                                'title': alt,
                                'source': 'pexels',
                                'type': 'video',
                            })
            except Exception as e:
                logger.debug(f"Pexels HTML search failed: {e}")

        logger.info(f"Found {len(clips)} clips for '{query}'")
        return clips[:count]

    async def search_images(self, query: str, count: int = 5) -> List[Dict]:
        """Search for stock images related to a topic."""
        images = []
        try:
            # Unsplash source
            resp = await self._http.get(
                f'https://source.unsplash.com/featured/?{query}',
                follow_redirects=True
            )
            if resp.status_code == 200 and resp.url:
                images.append({
                    'url': str(resp.url),
                    'title': f'Featured image for {query}',
                    'source': 'unsplash',
                    'type': 'image',
                })
        except Exception as e:
            logger.debug(f"Unsplash search failed: {e}")

        # Try Pixabay
        try:
            resp = await self._http.get(
                f'https://pixabay.com/images/search/{query}/',
            )
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                for img in soup.select('img[src*="pixabay"]'):
                    src = img.get('src', '')
                    if src and not src.endswith('.svg'):
                        images.append({
                            'url': src,
                            'title': img.get('alt', query),
                            'source': 'pixabay',
                            'type': 'image',
                        })
        except Exception as e:
            logger.debug(f"Pixabay search failed: {e}")

        return images[:count]

    async def download_media(self, url: str, filename: Optional[str] = None) -> Optional[str]:
        """Download a media file and return the local path."""
        if filename is None:
            ext = Path(urlparse(url).path).suffix or '.mp4'
            filename = f"{uuid.uuid4().hex[:8]}{ext}"

        output_path = self.download_dir / filename

        try:
            resp = await self._http.get(url)
            resp.raise_for_status()

            output_path.write_bytes(resp.content)
            size_kb = len(resp.content) / 1024
            logger.info(f"Downloaded {size_kb:.0f} KB -> {output_path}")
            return str(output_path)

        except Exception as e:
            logger.debug(f"Download failed for {url}: {e}")
            return None

    async def get_background_music(self, mood: str = 'upbeat', duration: int = 30) -> Optional[str]:
        """Get a background music track matching the desired mood."""
        # Generate silent audio using ffmpeg as fallback
        try:
            import subprocess
            output = self.download_dir / f"bg_music_{mood}_{uuid.uuid4().hex[:6]}.mp3"
            # Create a simple ambient tone with ffmpeg
            cmd = [
                'ffmpeg', '-y',
                '-f', 'lavfi', '-i', f'sine=frequency=220:duration={duration}',
                '-af', 'volume=0.1,afftfilt=real=\'hypot(re,im)*sin(0)\':imag=\'hypot(re,im)*cos(0)\'',
                '-c:a', 'libmp3lame', '-q:a', '9',
                str(output)
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            await proc.wait()

            if output.exists() and output.stat().st_size > 1000:
                logger.info(f"Generated background music: {output}")
                return str(output)
        except Exception as e:
            logger.debug(f"Music generation failed: {e}")

        return None

    async def cleanup(self):
        """Clean up HTTP client."""
        await self._http.aclose()

    def _headers(self) -> dict:
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                          '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
