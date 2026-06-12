"""Pydantic schemas for API request/response models."""

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search query parameters."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=10, ge=1, le=50, description="Results per page")


class SearchResultItem(BaseModel):
    """A single search result."""
    url: str
    title: str
    snippet: str
    score: float
    bm25_score: float
    pagerank: float
    domain: str


class SearchResponse(BaseModel):
    """Search endpoint response."""
    query: str
    total: int
    page: int
    size: int
    total_pages: int
    results: list[SearchResultItem]
    took_ms: float


class StatsResponse(BaseModel):
    """System stats response."""
    total_pages: int
    crawled_pages: int
    failed_pages: int
    total_links: int
    unique_domains: int
    index_doc_count: int = 0
    index_size_mb: float = 0.0
