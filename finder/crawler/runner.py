"""Crawl orchestrator — manages the full crawl pipeline."""

import asyncio
import signal
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from elasticsearch import Elasticsearch

from finder.config import settings
from finder.db.session import Database
from finder.db.models import PageDocument, LinkDocument, CrawlJobDocument
from finder.db import crud
from finder.crawler.frontier import URLFrontier
from finder.crawler.fetcher import Fetcher, FetchResult
from finder.crawler.robots import RobotsCache
from finder.crawler.parser import parse_html
from finder.crawler.storage import HTMLStorage

console = Console()


class CrawlRunner:
    """
    Main crawl orchestrator.
    
    Coordinates the frontier, fetcher, robots checker, parser, and storage
    to crawl web pages asynchronously.
    """

    def __init__(
        self,
        seed_urls: list[str] = None,
        max_depth: int = None,
        concurrency: int = None,
        max_pages_per_domain: int = 50,
    ):
        self.seed_urls = seed_urls or []
        self.max_depth = max_depth or settings.crawler_max_depth
        self.concurrency = concurrency or settings.crawler_concurrency
        self.max_pages_per_domain = max_pages_per_domain
        self._domain_counts: dict[str, int] = {}

        self.frontier = URLFrontier()
        self.fetcher = Fetcher(concurrency=self.concurrency)
        self.robots = RobotsCache()
        self.storage = HTMLStorage()

        # Initialize ES client
        self._es = None
        try:
            self._es = Elasticsearch(settings.elasticsearch_url)
        except Exception:
            pass

        # Stats
        self._pages_crawled = 0
        self._pages_failed = 0
        self._start_time = 0.0
        self._shutdown = False

    async def run(self, close_db: bool = True, handle_signals: bool = True):
        """Execute the crawl."""
        console.print("\n[bold cyan]🔍 Finder Crawler[/bold cyan]")
        console.print(f"  Seeds: {len(self.seed_urls)} URLs (will discover more if empty)")
        console.print(f"  Max depth: {self.max_depth}")
        console.print(f"  Concurrency: {self.concurrency}")
        console.print()

        # Connect to MongoDB if not already connected
        connected_here = False
        try:
            Database.get_db()
        except RuntimeError:
            await Database.connect()
            connected_here = True
            console.print("[green]✓[/green] Connected to MongoDB")

        # Start the HTTP client
        await self.fetcher.start()
        console.print("[green]✓[/green] HTTP client ready")

        # Automatic URL discovery if seed list is empty
        if not self.seed_urls:
            await self._discover_and_add_seeds()
            # Set job's seeds to whatever got loaded
            self.seed_urls = [entry.url for entry in self.frontier._queue]
        else:
            # Load seed URLs into frontier
            for url in self.seed_urls:
                self.frontier.add(url, priority=0.0, depth=0)

        # Create crawl job record
        job = CrawlJobDocument(
            seed_urls=self.seed_urls,
            max_depth=self.max_depth,
        )
        job_id = await crud.create_crawl_job(job)

        console.print(f"[green]✓[/green] Loaded {self.frontier.size} seed URLs into frontier\n")

        # Set up graceful shutdown
        if handle_signals:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, self._handle_shutdown)
                except NotImplementedError:
                    pass  # Windows doesn't support signal handlers in async

        self._start_time = time.monotonic()

        # Run crawl workers
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Crawling...", total=None)

            workers = [
                asyncio.create_task(self._worker(i, progress, task))
                for i in range(self.concurrency)
            ]

            # Wait for all workers to finish
            await asyncio.gather(*workers)

        # Finalize
        elapsed = time.monotonic() - self._start_time
        await self.fetcher.stop()

        # Update crawl job
        await crud.update_crawl_job(
            job_id,
            finished_at=datetime.now(timezone.utc),
            pages_crawled=self._pages_crawled,
            pages_failed=self._pages_failed,
            status="completed" if not self._shutdown else "interrupted",
        )

        # Print summary
        self._print_summary(elapsed)

        if close_db and connected_here:
            await Database.close()

    async def _discover_and_add_seeds(self):
        """Discover seed URLs from MongoDB links or fallback default hubs, and add to frontier."""
        discovered = []
        try:
            db = Database.get_db()
            # Fetch recent target URLs from links collection to crawl
            cursor = db.links.find({}, {"target_url": 1}).limit(1000)
            links = await cursor.to_list(length=1000)
            target_urls = list(set(link["target_url"] for link in links))

            # Filter to keep only those not yet crawled
            uncrawled = []
            for url in target_urls:
                if not await crud.url_exists(url):
                    uncrawled.append(url)

            if uncrawled:
                discovered = uncrawled
                console.print(f"  [cyan]Frontier[/cyan] Discovered {len(uncrawled)} uncrawled URLs from database links.")
        except Exception as e:
            console.print(f"  [yellow]Frontier[/yellow] Seed discovery failed: {e}")

        if not discovered:
            # Fallback to default hub list
            default_hubs = [
                "https://en.wikipedia.org/wiki/Web_search_engine",
                "https://en.wikipedia.org/wiki/PageRank",
                "https://news.ycombinator.com/",
                "https://docs.python.org/3/",
                "https://developer.mozilla.org/en-US/docs/Web",
            ]
            # Clear seen status for these hubs to allow re-crawling
            for url in default_hubs:
                normalized = self.frontier.normalize_url(url)
                if normalized:
                    url_h = self.frontier.url_hash(normalized)
                    if url_h in self.frontier._seen_urls:
                        self.frontier._seen_urls.remove(url_h)
                discovered.append(url)
            console.print(f"  [cyan]Frontier[/cyan] Database empty or all crawled. Seeding with {len(discovered)} default hubs.")

        # Load into frontier
        for url in discovered:
            self.frontier.add(url, priority=0.0, depth=0)

    async def _worker(self, worker_id: int, progress: Progress, task_id):
        """A single crawl worker that processes URLs from the frontier."""
        while not self._shutdown:
            entry = self.frontier.pop()
            if entry is None:
                # Wait a bit for new URLs to appear
                await asyncio.sleep(2.0)
                if self.frontier.is_empty():
                    if worker_id == 0:
                        # Thread 0 will try to discover new links to resume
                        await self._discover_and_add_seeds()
                    else:
                        await asyncio.sleep(2.0)
                continue

            url = entry.url
            depth = entry.depth

            # Skip if beyond max depth
            if depth > self.max_depth:
                continue

            # Check domain capping before fetching to prevent single-site hogging
            domain = urlparse(url).hostname or ""
            if self._domain_counts.get(domain, 0) >= self.max_pages_per_domain:
                continue

            # Check if already crawled
            try:
                if await crud.url_exists(url):
                    continue
            except Exception:
                pass

            # Check robots.txt
            try:
                allowed = await self.robots.can_fetch(url)
                if not allowed:
                    continue
            except Exception:
                continue  # Skip on robots.txt errors

            # Fetch the page
            result = await self.fetcher.fetch(url)

            if not result.ok:
                self._pages_failed += 1
                # Store failed page in DB for tracking
                failed_page = PageDocument(
                    url=url,
                    domain=urlparse(url).hostname or "",
                    status_code=result.status_code,
                    depth=depth,
                    status="failed",
                )
                await crud.upsert_page(failed_page)
                progress.update(task_id, advance=1, description=f"[red]✗[/red] {url[:60]}...")
                continue

            # Parse the HTML
            parse_result = parse_html(result.html, result.url)

            # Store raw HTML to disk
            content_hash = self.storage.store(
                url=result.url,
                html=result.html,
                status_code=result.status_code,
                headers=result.headers,
            )

            # Check for duplicate content
            is_dupe = await crud.content_hash_exists(content_hash)

            # Save page to MongoDB
            page = PageDocument(
                url=result.url,
                domain=urlparse(result.url).hostname or "",
                title=parse_result.title,
                extracted_text=parse_result.text[:50000],  # Limit text size
                content_hash=content_hash,
                status_code=result.status_code,
                depth=depth,
                status="crawled",
            )
            await crud.upsert_page(page)

            # Increment domain count
            page_domain = page.domain
            if page_domain:
                self._domain_counts[page_domain] = self._domain_counts.get(page_domain, 0) + 1

            # Automatically index into Elasticsearch in real-time
            if self._es:
                try:
                    from finder.indexer.es_indexer import INDEX_NAME
                    doc = {
                        "url": result.url,
                        "domain": page.domain,
                        "title": page.title,
                        "content": page.extracted_text[:100000],
                        "pagerank_score": page.pagerank_score,
                        "crawled_at": page.crawled_at,
                        "depth": page.depth,
                    }
                    if self._es.ping():
                        self._es.index(index=INDEX_NAME, id=page.content_hash or result.url, document=doc)
                except Exception:
                    pass

            # Save links to MongoDB
            link_docs = [
                LinkDocument(
                    source_url=result.url,
                    target_url=link.url,
                    anchor_text=link.anchor_text[:500],
                )
                for link in parse_result.links
            ]
            if link_docs:
                await crud.insert_links(link_docs)

            # Add discovered links to frontier (if not duplicate content)
            if not is_dupe and depth < self.max_depth:
                new_depth = depth + 1
                # Priority increases with depth (lower priority = crawled first)
                priority = float(new_depth)
                for link in parse_result.links:
                    link_domain = urlparse(link.url).hostname or ""
                    # Check domain capping to prevent single-domain monopolization
                    if self._domain_counts.get(link_domain, 0) < self.max_pages_per_domain:
                        self.frontier.add(link.url, priority=priority, depth=new_depth)

            self._pages_crawled += 1
            progress.update(
                task_id,
                advance=1,
                description=f"[green]✓[/green] {parse_result.title[:50] or url[:50]}",
            )

    def _handle_shutdown(self):
        """Handle graceful shutdown signal."""
        console.print("\n[yellow]⚠ Shutdown signal received. Finishing current pages...[/yellow]")
        self._shutdown = True

    def _print_summary(self, elapsed: float):
        """Print crawl summary table."""
        console.print()
        table = Table(title="Crawl Summary", show_header=False, border_style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Pages crawled", str(self._pages_crawled))
        table.add_row("Pages failed", str(self._pages_failed))
        table.add_row("URLs seen", str(self.frontier.seen_count))
        table.add_row("Queue remaining", str(self.frontier.size))
        table.add_row("HTML stored", str(self.storage.total_stored))
        table.add_row("Time elapsed", f"{elapsed:.1f}s")
        if elapsed > 0:
            table.add_row("Pages/sec", f"{self._pages_crawled / elapsed:.1f}")

        console.print(table)
        console.print()


async def run_crawl(seed_urls: list[str], max_depth: int = None, concurrency: int = None):
    """Entry point for running the crawler."""
    runner = CrawlRunner(
        seed_urls=seed_urls,
        max_depth=max_depth,
        concurrency=concurrency,
    )
    await runner.run()
