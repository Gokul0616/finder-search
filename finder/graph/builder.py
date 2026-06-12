"""Build a directed link graph from the crawled data in MongoDB."""

import networkx as nx
from rich.console import Console

from finder.db.session import Database
from finder.db import crud

console = Console()


async def build_link_graph() -> nx.DiGraph:
    """
    Build a NetworkX directed graph from the link data in MongoDB.
    
    Only includes links where both source and target URLs exist
    in our crawled corpus (pages collection).
    
    Returns:
        A NetworkX DiGraph with URLs as nodes.
    """
    console.print("[cyan]Building link graph from crawled data...[/cyan]")

    # Get all crawled page URLs
    pages = await crud.get_all_pages(projection={"url": 1, "_id": 0})
    crawled_urls = {page["url"] for page in pages}
    console.print(f"  Found {len(crawled_urls)} crawled pages")

    # Get all links
    links = await crud.get_all_links()
    console.print(f"  Found {len(links)} total links")

    # Build the graph — only include edges where both endpoints are in our corpus
    G = nx.DiGraph()

    # Add all crawled URLs as nodes
    G.add_nodes_from(crawled_urls)

    # Add edges (only where target is also in our corpus)
    edges_added = 0
    for link in links:
        source = link["source_url"]
        target = link["target_url"]
        if source in crawled_urls and target in crawled_urls and source != target:
            G.add_edge(source, target)
            edges_added += 1

    console.print(f"  Graph built: {G.number_of_nodes()} nodes, {edges_added} edges")

    # Graph statistics
    if G.number_of_nodes() > 0:
        weakly_connected = nx.number_weakly_connected_components(G)
        console.print(f"  Weakly connected components: {weakly_connected}")

        # Find nodes with most in-links (most "authoritative")
        in_degrees = sorted(G.in_degree(), key=lambda x: x[1], reverse=True)
        if in_degrees:
            console.print("  Top 5 pages by in-degree:")
            for url, degree in in_degrees[:5]:
                console.print(f"    {degree:>4} ← {url[:80]}")

    return G
