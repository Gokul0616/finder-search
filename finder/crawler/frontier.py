"""URL Frontier — priority queue with deduplication and URL normalization."""

import hashlib
import heapq
from dataclasses import dataclass, field
from urllib.parse import urlparse, urlunparse, urljoin
from typing import Optional


@dataclass(order=True)
class FrontierEntry:
    """An entry in the URL frontier priority queue."""
    priority: float
    url: str = field(compare=False)
    depth: int = field(compare=False)


class URLFrontier:
    """
    URL frontier with priority queue and deduplication.
    
    Lower priority values are popped first (0 = highest priority).
    URLs are normalized and deduplicated using their hash.
    """

    def __init__(self):
        self._queue: list[FrontierEntry] = []
        self._seen_urls: set[str] = set()  # Set of URL hashes
        self._total_added: int = 0
        self._total_popped: int = 0

    @staticmethod
    def normalize_url(url: str) -> Optional[str]:
        """
        Normalize a URL for consistent deduplication.
        
        - Lowercase scheme and host
        - Strip fragments (#...)
        - Strip trailing slashes from path
        - Remove default ports (80, 443)
        """
        try:
            parsed = urlparse(url)
            
            # Only handle http/https
            if parsed.scheme not in ("http", "https"):
                return None

            scheme = parsed.scheme.lower()
            host = parsed.hostname
            if not host:
                return None
            host = host.lower()

            # Remove default ports
            port = parsed.port
            if port == 80 and scheme == "http":
                port = None
            elif port == 443 and scheme == "https":
                port = None

            netloc = host
            if port:
                netloc = f"{host}:{port}"

            # Clean path
            path = parsed.path.rstrip("/") or "/"

            # Rebuild without fragment
            normalized = urlunparse((scheme, netloc, path, parsed.params, parsed.query, ""))
            return normalized
        except Exception:
            return None

    @staticmethod
    def url_hash(url: str) -> str:
        """Compute a SHA-256 hash of a URL for deduplication."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def add(self, url: str, priority: float = 1.0, depth: int = 0) -> bool:
        """
        Add a URL to the frontier.
        
        Returns True if the URL was added (not a duplicate).
        Returns False if the URL was already seen.
        """
        normalized = self.normalize_url(url)
        if normalized is None:
            return False

        url_h = self.url_hash(normalized)
        if url_h in self._seen_urls:
            return False

        self._seen_urls.add(url_h)
        entry = FrontierEntry(priority=priority, url=normalized, depth=depth)
        heapq.heappush(self._queue, entry)
        self._total_added += 1
        return True

    def add_many(self, urls: list[str], priority: float = 1.0, depth: int = 0) -> int:
        """Add multiple URLs. Returns count of actually added (non-duplicate) URLs."""
        added = 0
        for url in urls:
            if self.add(url, priority=priority, depth=depth):
                added += 1
        return added

    def pop(self) -> Optional[FrontierEntry]:
        """Pop the highest-priority URL from the frontier."""
        if not self._queue:
            return None
        entry = heapq.heappop(self._queue)
        self._total_popped += 1
        return entry

    def has_seen(self, url: str) -> bool:
        """Check if a URL has already been seen."""
        normalized = self.normalize_url(url)
        if normalized is None:
            return True  # Invalid URLs are "seen"
        return self.url_hash(normalized) in self._seen_urls

    def mark_seen(self, url: str):
        """Mark a URL as seen without adding it to the queue."""
        normalized = self.normalize_url(url)
        if normalized:
            self._seen_urls.add(self.url_hash(normalized))

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    @property
    def size(self) -> int:
        return len(self._queue)

    @property
    def seen_count(self) -> int:
        return len(self._seen_urls)

    @property
    def stats(self) -> dict:
        return {
            "queue_size": self.size,
            "seen_count": self.seen_count,
            "total_added": self._total_added,
            "total_popped": self._total_popped,
        }
