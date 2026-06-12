"""Async HTTP fetcher with rate limiting, retries, and politeness."""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

import httpx

from finder.config import settings


@dataclass
class FetchResult:
    """Result of fetching a URL."""
    url: str
    status_code: int = 0
    html: str = ""
    headers: dict = field(default_factory=dict)
    content_type: str = ""
    error: Optional[str] = None
    elapsed_ms: float = 0.0

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400


class DomainRateLimiter:
    """Per-domain rate limiter using token bucket algorithm with per-domain locks."""

    def __init__(self, rate: float = 2.0):
        """
        Args:
            rate: Maximum requests per second per domain.
        """
        self._rate = rate
        self._domain_last_request: dict[str, float] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def _get_lock(self, domain: str) -> asyncio.Lock:
        async with self._global_lock:
            if domain not in self._locks:
                self._locks[domain] = asyncio.Lock()
            return self._locks[domain]

    async def acquire(self, domain: str):
        """Wait until we're allowed to make a request to this domain."""
        lock = await self._get_lock(domain)
        async with lock:
            now = time.monotonic()
            last = self._domain_last_request.get(domain, 0.0)
            min_interval = 1.0 / self._rate
            elapsed = now - last

            if elapsed < min_interval:
                wait_time = min_interval - elapsed
                await asyncio.sleep(wait_time)

            self._domain_last_request[domain] = time.monotonic()


class Fetcher:
    """
    Async HTTP fetcher with connection pooling, rate limiting, and retries.
    
    Uses httpx.AsyncClient for HTTP/2 support and connection reuse.
    """

    def __init__(
        self,
        concurrency: int = None,
        rate_limit: float = None,
        user_agent: str = None,
        max_retries: int = 3,
        timeout: float = 15.0,
    ):
        self._concurrency = concurrency or settings.crawler_concurrency
        self._rate_limiter = DomainRateLimiter(rate=rate_limit or settings.crawler_rate_limit)
        self._user_agent = user_agent or settings.crawler_user_agent
        self._max_retries = max_retries
        self._timeout = timeout
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._client: Optional[httpx.AsyncClient] = None

        # Stats
        self.total_fetched = 0
        self.total_errors = 0

    async def start(self):
        """Initialize the HTTP client."""
        self._client = httpx.AsyncClient(
            http2=True,
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
            max_redirects=5,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
            },
            limits=httpx.Limits(
                max_connections=max(1000, self._concurrency * 4),
                max_keepalive_connections=max(500, self._concurrency * 2),
            ),
        )

    async def stop(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def fetch(self, url: str) -> FetchResult:
        """
        Fetch a URL with rate limiting, concurrency control, and retries.
        
        Implements exponential backoff on retries.
        """
        async with self._semaphore:
            domain = urlparse(url).hostname or ""
            await self._rate_limiter.acquire(domain)

            for attempt in range(self._max_retries):
                try:
                    start_time = time.monotonic()
                    response = await self._client.get(url)
                    elapsed = (time.monotonic() - start_time) * 1000

                    content_type = response.headers.get("content-type", "")

                    # Skip non-HTML responses
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        self.total_fetched += 1
                        return FetchResult(
                            url=str(response.url),  # Final URL after redirects
                            status_code=response.status_code,
                            content_type=content_type,
                            error=f"Non-HTML content type: {content_type}",
                            elapsed_ms=elapsed,
                        )

                    self.total_fetched += 1
                    return FetchResult(
                        url=str(response.url),
                        status_code=response.status_code,
                        html=response.text,
                        headers=dict(response.headers),
                        content_type=content_type,
                        elapsed_ms=elapsed,
                    )

                except httpx.TimeoutException:
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    self.total_errors += 1
                    return FetchResult(url=url, error="Timeout")

                except httpx.TooManyRedirects:
                    self.total_errors += 1
                    return FetchResult(url=url, error="Too many redirects")

                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    # Retry on 429 (rate limited) and 5xx (server errors)
                    if status in (429, 500, 502, 503, 504) and attempt < self._max_retries - 1:
                        wait = 2 ** attempt
                        if status == 429:
                            # Respect Retry-After header if present
                            retry_after = e.response.headers.get("Retry-After")
                            if retry_after and retry_after.isdigit():
                                wait = int(retry_after)
                        await asyncio.sleep(wait)
                        continue
                    self.total_errors += 1
                    return FetchResult(
                        url=url,
                        status_code=status,
                        error=f"HTTP {status}",
                    )

                except Exception as e:
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    self.total_errors += 1
                    return FetchResult(url=url, error=str(e))

        # Should never reach here
        return FetchResult(url=url, error="Unknown error")
