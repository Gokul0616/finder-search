"""Raw HTML storage — save crawled pages to disk with gzip compression."""

import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from finder.config import settings


class HTMLStorage:
    """
    Store raw HTML pages to disk organized by domain.
    
    Structure: {base_dir}/{domain}/{url_hash}.html.gz
    Each HTML file has a companion .meta.json with metadata.
    """

    def __init__(self, base_dir: str = None):
        self._base_dir = Path(base_dir or settings.raw_html_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self.total_stored = 0

    @staticmethod
    def url_to_hash(url: str) -> str:
        """Generate a filesystem-safe hash from a URL."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    def _get_paths(self, url: str) -> tuple[Path, Path]:
        """Get the HTML and metadata file paths for a URL."""
        domain = urlparse(url).hostname or "unknown"
        url_hash = self.url_to_hash(url)
        domain_dir = self._base_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        html_path = domain_dir / f"{url_hash}.html.gz"
        meta_path = domain_dir / f"{url_hash}.meta.json"
        return html_path, meta_path

    def store(self, url: str, html: str, status_code: int = 200, headers: dict = None) -> str:
        """
        Save raw HTML to disk with gzip compression.
        
        Args:
            url: The page URL.
            html: Raw HTML content.
            status_code: HTTP status code.
            headers: Response headers.
        
        Returns:
            The content hash (SHA-256 of the HTML).
        """
        html_path, meta_path = self._get_paths(url)

        # Compute content hash
        content_hash = hashlib.sha256(html.encode("utf-8")).hexdigest()

        # Store compressed HTML
        with gzip.open(html_path, "wt", encoding="utf-8") as f:
            f.write(html)

        # Store metadata
        metadata = {
            "url": url,
            "status_code": status_code,
            "content_hash": content_hash,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "size_bytes": len(html.encode("utf-8")),
            "content_type": (headers or {}).get("content-type", ""),
        }
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

        self.total_stored += 1
        return content_hash

    def load(self, url: str) -> tuple[str, dict]:
        """
        Load a stored HTML page and its metadata.
        
        Returns:
            Tuple of (html_content, metadata_dict).
        """
        html_path, meta_path = self._get_paths(url)

        html = ""
        if html_path.exists():
            with gzip.open(html_path, "rt", encoding="utf-8") as f:
                html = f.read()

        metadata = {}
        if meta_path.exists():
            with open(meta_path, "r") as f:
                metadata = json.load(f)

        return html, metadata

    def exists(self, url: str) -> bool:
        """Check if a page has been stored."""
        html_path, _ = self._get_paths(url)
        return html_path.exists()

    @property
    def stats(self) -> dict:
        """Get storage statistics."""
        total_files = 0
        total_size = 0
        domains = set()

        for domain_dir in self._base_dir.iterdir():
            if domain_dir.is_dir():
                domains.add(domain_dir.name)
                for f in domain_dir.glob("*.html.gz"):
                    total_files += 1
                    total_size += f.stat().st_size

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "domains": len(domains),
        }
