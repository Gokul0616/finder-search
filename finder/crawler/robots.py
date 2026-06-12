"""robots.txt parser with caching."""

import asyncio
import time
from typing import Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

from finder.config import settings


class RobotsCache:
    """
    Cache of parsed robots.txt files per domain.
    
    Fetches and parses robots.txt on first access per domain,
    then caches the result with a configurable TTL.
    """

    def __init__(self, ttl_seconds: int = 3600, user_agent: str = None):
        self._cache: dict[str, tuple[RobotFileParser, float]] = {}  # domain → (parser, timestamp)
        self._ttl = ttl_seconds
        self._user_agent = user_agent or settings.crawler_user_agent
        self._lock = asyncio.Lock()

    def _get_robots_url(self, url: str) -> str:
        """Get the robots.txt URL for a given page URL."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        return urlparse(url).netloc

    async def _fetch_robots(self, robots_url: str) -> Optional[RobotFileParser]:
        """Fetch and parse a robots.txt file."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    parser = RobotFileParser()
                    parser.parse(response.text.splitlines())
                    return parser
                else:
                    # If robots.txt doesn't exist or error, allow everything
                    parser = RobotFileParser()
                    parser.allow_all = True
                    return parser
        except Exception:
            # On network errors, be permissive
            parser = RobotFileParser()
            parser.allow_all = True
            return parser

    async def can_fetch(self, url: str) -> bool:
        """
        Check if our crawler is allowed to fetch this URL per robots.txt.
        
        Caches the robots.txt parser per domain with TTL.
        """
        domain = self._get_domain(url)

        async with self._lock:
            # Check cache
            if domain in self._cache:
                parser, cached_at = self._cache[domain]
                if time.time() - cached_at < self._ttl:
                    return parser.can_fetch(self._user_agent, url)

            # Fetch fresh robots.txt
            robots_url = self._get_robots_url(url)

        # Fetch outside the lock to avoid blocking
        parser = await self._fetch_robots(robots_url)
        if parser is None:
            return True  # Default to permissive

        async with self._lock:
            self._cache[domain] = (parser, time.time())

        return parser.can_fetch(self._user_agent, url)

    async def get_crawl_delay(self, url: str) -> Optional[float]:
        """Get the Crawl-delay directive for our user agent, if specified."""
        domain = self._get_domain(url)

        async with self._lock:
            if domain in self._cache:
                parser, _ = self._cache[domain]
                delay = parser.crawl_delay(self._user_agent)
                return float(delay) if delay else None

        # If not cached yet, fetch first
        await self.can_fetch(url)

        async with self._lock:
            if domain in self._cache:
                parser, _ = self._cache[domain]
                delay = parser.crawl_delay(self._user_agent)
                return float(delay) if delay else None

        return None
