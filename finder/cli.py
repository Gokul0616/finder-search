"""Finder CLI — command-line interface for crawling, ranking, indexing, and serving."""

import asyncio
from pathlib import Path

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="Finder")
def cli():
    """🔍 Finder — A search engine built from scratch."""
    pass


@cli.command()
@click.option("--seeds", "-s", type=click.Path(exists=True), default=None, help="Path to seed URLs file (one URL per line)")
@click.option("--url", "-u", multiple=True, help="Individual seed URL(s)")
@click.option("--depth", "-d", type=int, default=None, help="Maximum crawl depth (default: 3)")
@click.option("--workers", "-w", type=int, default=None, help="Number of concurrent workers (default: 10)")
def crawl(seeds, url, depth, workers):
    """Crawl web pages starting from seed URLs."""
    from finder.crawler.runner import run_crawl

    seed_urls = list(url) if url else []

    # Load from file if provided
    if seeds:
        with open(seeds) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    seed_urls.append(line)

    # Default seed URLs if none provided
    if not seed_urls:
        default_seeds = Path(__file__).parent.parent / "scripts" / "seed_urls.txt"
        if default_seeds.exists():
            with open(default_seeds) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        seed_urls.append(line)

    if not seed_urls:
        console.print("[red]No seed URLs provided. Use --seeds or --url.[/red]")
        return

    console.print(f"Starting crawl with {len(seed_urls)} seed URLs...")
    asyncio.run(run_crawl(seed_urls=seed_urls, max_depth=depth, concurrency=workers))


@cli.command()
@click.option("--alpha", type=float, default=0.85, help="Damping factor (default: 0.85)")
@click.option("--max-iter", type=int, default=100, help="Maximum iterations (default: 100)")
def rank(alpha, max_iter):
    """Compute PageRank scores from the link graph."""
    from finder.graph.pagerank import compute_pagerank

    console.print("[bold cyan]Computing PageRank...[/bold cyan]")
    asyncio.run(compute_pagerank(alpha=alpha, max_iter=max_iter))
    console.print("[green]✓ PageRank computation complete.[/green]")


@cli.command()
def index():
    """Index all crawled pages into Elasticsearch."""
    from finder.indexer.es_indexer import ESIndexer

    indexer = ESIndexer()
    asyncio.run(indexer.index_all_pages())
    indexer.close()
    console.print("[green]✓ Indexing complete.[/green]")


@cli.command()
@click.option("--host", type=str, default=None, help="Host to bind (default: 0.0.0.0)")
@click.option("--port", "-p", type=int, default=None, help="Port (default: 8000)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host, port, reload):
    """Start the Finder search API server."""
    import uvicorn
    from finder.config import settings

    host = host or settings.api_host
    port = port or settings.api_port

    console.print(f"\n[bold cyan]🔍 Finder Search Engine[/bold cyan]")
    console.print(f"  API:      http://{host}:{port}/api/search?q=python")
    console.print(f"  Frontend: http://{host}:{port}/")
    console.print(f"  Docs:     http://{host}:{port}/docs")
    console.print()

    uvicorn.run(
        "finder.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
@click.option("--seeds", "-s", type=click.Path(exists=True), default=None, help="Seed URLs file")
@click.option("--depth", "-d", type=int, default=None, help="Max crawl depth")
@click.option("--workers", "-w", type=int, default=None, help="Concurrent workers")
def pipeline(seeds, depth, workers):
    """Run the full pipeline: crawl → rank → index → serve."""
    from finder.crawler.runner import run_crawl
    from finder.graph.pagerank import compute_pagerank
    from finder.indexer.es_indexer import ESIndexer

    # Step 1: Crawl
    seed_urls = []
    if seeds:
        with open(seeds) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    seed_urls.append(line)
    else:
        default_seeds = Path(__file__).parent.parent / "scripts" / "seed_urls.txt"
        if default_seeds.exists():
            with open(default_seeds) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        seed_urls.append(line)

    if seed_urls:
        console.print("\n[bold]Step 1/4: Crawling[/bold]")
        asyncio.run(run_crawl(seed_urls=seed_urls, max_depth=depth, concurrency=workers))
    else:
        console.print("[yellow]No seed URLs — skipping crawl[/yellow]")

    # Step 2: PageRank
    console.print("\n[bold]Step 2/4: Computing PageRank[/bold]")
    asyncio.run(compute_pagerank())

    # Step 3: Index
    console.print("\n[bold]Step 3/4: Indexing[/bold]")
    indexer = ESIndexer()
    asyncio.run(indexer.index_all_pages())
    indexer.close()

    # Step 4: Serve
    console.print("\n[bold]Step 4/4: Starting server[/bold]")
    import uvicorn
    from finder.config import settings
    uvicorn.run("finder.api.main:app", host=settings.api_host, port=settings.api_port)


@cli.command()
def stats():
    """Show crawl and index statistics."""
    from finder.db.session import Database
    from finder.db import crud
    from rich.table import Table

    async def _stats():
        await Database.connect()
        s = await crud.get_crawl_stats()
        await Database.close()
        return s

    s = asyncio.run(_stats())

    table = Table(title="Finder Statistics", border_style="cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Total pages", str(s["total_pages"]))
    table.add_row("Crawled pages", str(s["crawled_pages"]))
    table.add_row("Failed pages", str(s["failed_pages"]))
    table.add_row("Total links", str(s["total_links"]))
    table.add_row("Unique domains", str(s["unique_domains"]))

    console.print(table)


if __name__ == "__main__":
    cli()
