"""Elasticsearch indexer — creates index and bulk indexes crawled pages."""

from elasticsearch import Elasticsearch, helpers
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

from finder.config import settings
from finder.db.session import Database
from finder.db import crud
from finder.indexer.extractor import extract_clean_text
from finder.crawler.storage import HTMLStorage

console = Console()

# Elasticsearch index name
INDEX_NAME = "finder_pages"

# Index mapping with custom analyzer for BM25 search
INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "finder_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": ["lowercase", "stop", "porter_stem"],
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "url": {"type": "keyword"},
            "domain": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "finder_analyzer",
                "fields": {
                    "raw": {"type": "keyword"}
                },
            },
            "content": {
                "type": "text",
                "analyzer": "finder_analyzer",
            },
            "pagerank_score": {"type": "float"},
            "crawled_at": {"type": "date"},
            "depth": {"type": "integer"},
        }
    },
}


class ESIndexer:
    """Manages Elasticsearch indexing of crawled pages."""

    def __init__(self):
        self._es = Elasticsearch(settings.elasticsearch_url)
        self._storage = HTMLStorage()

    def create_index(self, delete_existing: bool = True):
        """Create the Elasticsearch index with custom mapping."""
        if self._es.indices.exists(index=INDEX_NAME):
            if delete_existing:
                console.print(f"  Deleting existing index '{INDEX_NAME}'...")
                self._es.indices.delete(index=INDEX_NAME)
            else:
                console.print(f"  Index '{INDEX_NAME}' already exists, skipping creation.")
                return

        self._es.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
        console.print(f"[green]✓[/green] Created index '{INDEX_NAME}'")

    async def index_all_pages(self):
        """
        Index all crawled pages from MongoDB into Elasticsearch.
        
        For each page:
        1. Load the stored raw HTML from disk
        2. Extract clean text using trafilatura
        3. Bulk index into Elasticsearch
        """
        console.print("\n[bold cyan]📚 Finder Indexer[/bold cyan]")

        await Database.connect()
        console.print("[green]✓[/green] Connected to MongoDB")

        # Check ES connection
        if not self._es.ping():
            console.print("[red]✗ Cannot connect to Elasticsearch[/red]")
            console.print(f"  URL: {settings.elasticsearch_url}")
            console.print("  Make sure Elasticsearch is running locally.")
            return

        console.print("[green]✓[/green] Connected to Elasticsearch")

        # Create/recreate the index
        self.create_index()

        # Get all crawled pages from MongoDB
        pages = await crud.get_all_pages()
        console.print(f"  Found {len(pages)} crawled pages to index")

        if not pages:
            console.print("[yellow]No pages to index.[/yellow]")
            return

        # Prepare documents for bulk indexing
        docs = []
        errors = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Extracting & indexing...", total=len(pages))

            for page in pages:
                try:
                    url = page["url"]

                    # Try to load raw HTML from disk for better extraction
                    html_content = ""
                    if self._storage.exists(url):
                        html_content, _ = self._storage.load(url)

                    # Extract clean text
                    if html_content:
                        extracted = extract_clean_text(html_content, url)
                        title = extracted["title"]
                        content = extracted["text"]
                    else:
                        # Fall back to text stored in MongoDB
                        title = page.get("title", "")
                        content = page.get("extracted_text", "")

                    if not content:
                        progress.update(task, advance=1)
                        continue

                    doc = {
                        "_index": INDEX_NAME,
                        "_id": page.get("content_hash", url),
                        "_source": {
                            "url": url,
                            "domain": page.get("domain", ""),
                            "title": title,
                            "content": content[:100000],  # Limit content size
                            "pagerank_score": page.get("pagerank_score", 0.0),
                            "crawled_at": page.get("crawled_at"),
                            "depth": page.get("depth", 0),
                        },
                    }
                    docs.append(doc)

                except Exception as e:
                    errors += 1

                progress.update(
                    task, advance=1,
                    description=f"Processing: {page.get('url', '')[:50]}",
                )

        # Bulk index
        if docs:
            console.print(f"\n  Bulk indexing {len(docs)} documents...")
            success, failed = helpers.bulk(
                self._es,
                docs,
                chunk_size=500,
                raise_on_error=False,
            )
            console.print(f"[green]✓[/green] Indexed {success} documents ({failed} failed)")
        else:
            console.print("[yellow]No documents to index.[/yellow]")

        if errors:
            console.print(f"[yellow]  {errors} extraction errors[/yellow]")

        # Refresh index to make docs searchable immediately
        self._es.indices.refresh(index=INDEX_NAME)

        # Print index stats
        stats = self._es.indices.stats(index=INDEX_NAME)
        doc_count = stats["indices"][INDEX_NAME]["primaries"]["docs"]["count"]
        size_bytes = stats["indices"][INDEX_NAME]["primaries"]["store"]["size_in_bytes"]
        console.print(f"  Index size: {size_bytes / (1024*1024):.1f} MB, {doc_count} docs")

        await Database.close()

    def close(self):
        """Close the Elasticsearch client."""
        self._es.close()
