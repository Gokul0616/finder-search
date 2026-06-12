"""FastAPI application — the Finder query server."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from finder.config import settings
from finder.api.routes.search import router as search_router
from finder.api.dependencies import get_es_client, close_clients
from finder.db.session import Database
from finder.db import crud
from finder.api.schemas import StatsResponse
from finder.indexer.es_indexer import INDEX_NAME


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    await Database.connect()
    print("✓ Connected to MongoDB")

    try:
        es = get_es_client()
        if es.ping():
            print("✓ Connected to Elasticsearch")
        else:
            print("⚠ Elasticsearch not available — search will not work")
    except Exception:
        print("⚠ Elasticsearch not available — search will not work")

    yield

    # Shutdown
    close_clients()
    await Database.close()
    print("✓ Connections closed")


app = FastAPI(
    title="Finder Search Engine",
    description="A search engine built from scratch — crawl, index, rank, search.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend (dev on port 3000, prod anywhere)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(search_router, prefix="/api", tags=["search"])


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics — crawl counts, index size, etc."""
    # Get crawl stats from MongoDB
    db_stats = await crud.get_crawl_stats()

    # Get index stats from Elasticsearch
    index_doc_count = 0
    index_size_mb = 0.0
    try:
        es = get_es_client()
        if es.indices.exists(index=INDEX_NAME):
            stats = es.indices.stats(index=INDEX_NAME)
            index_doc_count = stats["indices"][INDEX_NAME]["primaries"]["docs"]["count"]
            size_bytes = stats["indices"][INDEX_NAME]["primaries"]["store"]["size_in_bytes"]
            index_size_mb = round(size_bytes / (1024 * 1024), 2)
    except Exception:
        pass

    return StatsResponse(
        total_pages=db_stats["total_pages"],
        crawled_pages=db_stats["crawled_pages"],
        failed_pages=db_stats["failed_pages"],
        total_links=db_stats["total_links"],
        unique_domains=db_stats["unique_domains"],
        index_doc_count=index_doc_count,
        index_size_mb=index_size_mb,
    )
