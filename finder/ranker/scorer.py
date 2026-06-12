"""Combined BM25 + PageRank scorer for search results."""

import re
from dataclasses import dataclass
from typing import Optional

from elasticsearch import Elasticsearch

from finder.config import settings
from finder.indexer.es_indexer import INDEX_NAME


@dataclass
class SearchResult:
    """A single search result with combined scoring."""
    url: str
    title: str
    snippet: str
    bm25_score: float
    pagerank_score: float
    final_score: float
    domain: str


class Scorer:
    """
    Combined search scorer using BM25 (from Elasticsearch) + PageRank.
    
    final_score = α * normalized_bm25 + β * pagerank_score
    
    Additional boosts:
    - Title match: +20% if query appears in title
    - Exact phrase: +15% if exact query phrase appears in content
    """

    def __init__(
        self,
        es_client: Elasticsearch,
        alpha: float = None,
        beta: float = None,
    ):
        self._es = es_client
        self._alpha = alpha or settings.ranker_alpha
        self._beta = beta or settings.ranker_beta

    def search(
        self,
        query: str,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[SearchResult], int, float]:
        """
        Search for pages matching the query with combined BM25 + PageRank scoring.
        
        Args:
            query: Search query string.
            page: Page number (1-indexed).
            size: Results per page.
        
        Returns:
            Tuple of (results, total_hits, took_ms).
        """
        from_offset = (page - 1) * size

        # Elasticsearch query using multi_match with title boost
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "content"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            },
            "highlight": {
                "fields": {
                    "content": {
                        "fragment_size": 200,
                        "number_of_fragments": 2,
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"],
                    },
                    "title": {
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"],
                    },
                },
            },
            "from": from_offset,
            "size": size * 2,  # Fetch extra to re-rank
            "_source": ["url", "title", "domain", "pagerank_score", "content"],
            "sort": ["_score"],
        }

        response = self._es.search(index=INDEX_NAME, body=search_body)

        took_ms = response["took"]
        total_hits = response["hits"]["total"]["value"]
        hits = response["hits"]["hits"]

        if not hits:
            return [], total_hits, took_ms

        # Normalize BM25 scores to [0, 1] within this result set
        max_bm25 = max(h["_score"] for h in hits) if hits else 1.0
        if max_bm25 == 0:
            max_bm25 = 1.0

        results = []
        query_lower = query.lower()

        for hit in hits:
            source = hit["_source"]
            bm25_raw = hit["_score"]
            bm25_normalized = bm25_raw / max_bm25
            pagerank = source.get("pagerank_score", 0.0)

            # Combined score
            combined = self._alpha * bm25_normalized + self._beta * pagerank

            # Title match boost
            title = source.get("title", "")
            if query_lower in title.lower():
                combined *= 1.20  # +20% for title match

            # Exact phrase boost: check if the exact query appears in content
            content = source.get("content", "")
            if query_lower in content.lower():
                combined *= 1.15  # +15% for exact phrase

            # Generate snippet from highlights or content
            snippet = self._generate_snippet(hit, query)

            results.append(SearchResult(
                url=source.get("url", ""),
                title=title or "Untitled",
                snippet=snippet,
                bm25_score=bm25_normalized,
                pagerank_score=pagerank,
                final_score=combined,
                domain=source.get("domain", ""),
            ))

        # Re-rank by combined score
        results.sort(key=lambda r: r.final_score, reverse=True)

        # Return only the requested page size
        return results[:size], total_hits, took_ms

    def _generate_snippet(self, hit: dict, query: str) -> str:
        """Generate a snippet from ES highlights or content."""
        highlight = hit.get("highlight", {})

        # Use highlighted content if available
        if "content" in highlight:
            return " … ".join(highlight["content"][:2])

        # Fall back to first N characters of content with query context
        content = hit["_source"].get("content", "")
        if not content:
            return ""

        # Try to find query context in content
        query_lower = query.lower()
        content_lower = content.lower()
        pos = content_lower.find(query_lower)

        if pos >= 0:
            # Extract ~200 chars around the match
            start = max(0, pos - 80)
            end = min(len(content), pos + len(query) + 120)
            snippet = content[start:end].strip()
            if start > 0:
                snippet = "…" + snippet
            if end < len(content):
                snippet = snippet + "…"

            # Highlight the match
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            snippet = pattern.sub(lambda m: f"<mark>{m.group()}</mark>", snippet)
            return snippet

        # Just return first 200 chars
        return content[:200] + ("…" if len(content) > 200 else "")
