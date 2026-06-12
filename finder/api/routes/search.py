"""Search API endpoint."""

import hashlib
import json
import math
from typing import Optional

from fastapi import APIRouter, Query, Depends

from finder.api.schemas import SearchResponse, SearchResultItem
from finder.api.dependencies import get_scorer, get_redis_client
from finder.ranker.scorer import Scorer

router = APIRouter()

# Cache TTL in seconds
CACHE_TTL = 300  # 5 minutes


def _cache_key(query: str, page: int, size: int) -> str:
    """Generate a cache key for a search query."""
    raw = f"search:{query}:{page}:{size}"
    return f"finder:search:{hashlib.md5(raw.encode()).hexdigest()}"


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=50, description="Results per page"),
):
    """
    Search for web pages.
    
    Returns ranked results combining BM25 relevance and PageRank authority scores.
    Results include highlighted snippets showing matched terms.
    """
    scorer = get_scorer()

    # Try Redis cache first
    try:
        redis_client = get_redis_client()
        cache_key = _cache_key(q, page, size)
        cached = redis_client.get(cache_key)
        if cached:
            return SearchResponse(**json.loads(cached))
    except Exception:
        # Redis not available, skip caching
        redis_client = None

    # Execute search
    results, total_hits, took_ms = await scorer.search(query=q, page=page, size=size)

    # Build response
    result_items = [
        SearchResultItem(
            url=r.url,
            title=r.title,
            snippet=r.snippet,
            score=round(r.final_score, 4),
            bm25_score=round(r.bm25_score, 4),
            pagerank=round(r.pagerank_score, 4),
            domain=r.domain,
        )
        for r in results
    ]

    total_pages = math.ceil(total_hits / size) if total_hits > 0 else 0

    response = SearchResponse(
        query=q,
        total=total_hits,
        page=page,
        size=size,
        total_pages=total_pages,
        results=result_items,
        took_ms=took_ms,
    )

    # Cache the response
    try:
        if redis_client:
            redis_client.setex(cache_key, CACHE_TTL, response.model_dump_json())
    except Exception:
        pass

    return response
