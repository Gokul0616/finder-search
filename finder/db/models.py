"""Pydantic models representing MongoDB documents."""

from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional


class PageDocument(BaseModel):
    """A crawled web page stored in the 'pages' collection."""
    url: str
    domain: str
    title: str = ""
    extracted_text: str = ""
    content_hash: str = ""  # SHA-256 of the page content
    status_code: int = 0
    crawled_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    depth: int = 0
    pagerank_score: float = 0.0
    status: str = "crawled"  # crawled, failed, indexed

    def to_dict(self) -> dict:
        d = self.model_dump()
        return d


class LinkDocument(BaseModel):
    """A link between two pages stored in the 'links' collection."""
    source_url: str
    target_url: str
    anchor_text: str = ""

    def to_dict(self) -> dict:
        return self.model_dump()


class CrawlJobDocument(BaseModel):
    """A crawl job record stored in the 'crawl_jobs' collection."""
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    pages_crawled: int = 0
    pages_failed: int = 0
    status: str = "running"  # running, completed, failed
    seed_urls: list[str] = []
    max_depth: int = 3

    def to_dict(self) -> dict:
        return self.model_dump()
