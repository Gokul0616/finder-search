"""PageRank computation using NetworkX."""

import networkx as nx
from rich.console import Console
from rich.table import Table

from finder.db.session import Database
from finder.db import crud
from finder.graph.builder import build_link_graph

console = Console()


async def compute_pagerank(alpha: float = 0.85, max_iter: int = 100) -> dict[str, float]:
    """
    Compute PageRank scores for all crawled pages.
    
    Args:
        alpha: Damping factor (probability of following a link vs random jump).
               Default 0.85 (standard value from the original PageRank paper).
        max_iter: Maximum iterations for convergence.
    
    Returns:
        Dictionary of {url: pagerank_score}.
    """
    await Database.connect()

    # Build the link graph
    G = await build_link_graph()

    if G.number_of_nodes() == 0:
        console.print("[yellow]No pages to rank.[/yellow]")
        return {}

    console.print(f"\n[cyan]Computing PageRank (α={alpha}, max_iter={max_iter})...[/cyan]")

    # Compute PageRank
    try:
        scores = nx.pagerank(G, alpha=alpha, max_iter=max_iter)
    except nx.PowerIterationFailedConvergence:
        console.print("[yellow]⚠ PageRank did not converge, using partial results[/yellow]")
        scores = nx.pagerank(G, alpha=alpha, max_iter=max_iter, tol=1e-4)

    # Normalize scores to [0, 1] range
    if scores:
        max_score = max(scores.values())
        min_score = min(scores.values())
        score_range = max_score - min_score
        if score_range > 0:
            normalized = {url: (score - min_score) / score_range for url, score in scores.items()}
        else:
            normalized = {url: 1.0 for url in scores}
    else:
        normalized = {}

    # Write scores back to MongoDB
    console.print(f"  Writing {len(normalized)} PageRank scores to database...")
    await crud.update_pagerank_scores(normalized)

    # Print top results
    _print_top_pages(normalized)

    await Database.close()
    return normalized


def _print_top_pages(scores: dict[str, float], top_n: int = 15):
    """Print the top-ranked pages in a table."""
    sorted_pages = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    table = Table(title=f"Top {top_n} Pages by PageRank", border_style="cyan")
    table.add_column("Rank", justify="right", style="bold")
    table.add_column("Score", justify="right", style="green")
    table.add_column("URL", style="blue")

    for i, (url, score) in enumerate(sorted_pages[:top_n], 1):
        table.add_row(str(i), f"{score:.6f}", url[:100])

    console.print()
    console.print(table)

    console.print(f"\n  Total pages ranked: {len(scores)}")
    if scores:
        avg_score = sum(scores.values()) / len(scores)
        console.print(f"  Average score: {avg_score:.6f}")
