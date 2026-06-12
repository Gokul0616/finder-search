"""HTML parser — extract title, clean text, and outbound links."""

from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup


# File extensions to skip when extracting links
SKIP_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".rar", ".7z",
    ".mp3", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".wav",
    ".exe", ".dmg", ".deb", ".rpm",
    ".css", ".js", ".json", ".xml", ".rss", ".atom",
    ".woff", ".woff2", ".ttf", ".eot",
}

# Schemes to skip
SKIP_SCHEMES = {"mailto", "tel", "javascript", "ftp", "data", "blob"}


@dataclass
class ExtractedLink:
    """A link extracted from an HTML page."""
    url: str
    anchor_text: str = ""


@dataclass
class ParseResult:
    """Result of parsing an HTML page."""
    title: str = ""
    text: str = ""
    links: list[ExtractedLink] = field(default_factory=list)
    meta_description: str = ""
    language: str = ""


def parse_html(html: str, base_url: str) -> ParseResult:
    """
    Parse HTML content and extract title, clean text, and outbound links.
    
    Args:
        html: Raw HTML string.
        base_url: The URL of the page (used to resolve relative links).
    
    Returns:
        ParseResult with title, extracted text, and list of links.
    """
    soup = BeautifulSoup(html, "lxml")

    # Extract title
    title = ""
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        title = title_tag.string.strip()

    # Extract meta description
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "").strip()

    # Extract language
    lang = ""
    html_tag = soup.find("html")
    if html_tag:
        lang = html_tag.get("lang", "").strip()

    # Remove non-content elements before text extraction
    for tag in soup.find_all(["script", "style", "noscript", "header", "footer", "nav", "aside"]):
        tag.decompose()

    # Extract text
    text = soup.get_text(separator=" ", strip=True)
    # Collapse multiple whitespace
    text = " ".join(text.split())

    # Extract links
    links = []
    seen_urls = set()

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href:
            continue

        # Resolve relative URLs
        try:
            absolute_url = urljoin(base_url, href)
        except Exception:
            continue

        # Parse and validate
        parsed = urlparse(absolute_url)

        # Skip unwanted schemes
        if parsed.scheme in SKIP_SCHEMES or parsed.scheme not in ("http", "https"):
            continue

        # Skip file extensions we don't want to crawl
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in SKIP_EXTENSIONS):
            continue

        # Normalize: strip fragment
        clean_url = absolute_url.split("#")[0]
        if not clean_url:
            continue

        # Dedup within this page
        if clean_url in seen_urls:
            continue
        seen_urls.add(clean_url)

        # Get anchor text
        anchor = a_tag.get_text(strip=True)

        links.append(ExtractedLink(url=clean_url, anchor_text=anchor))

    return ParseResult(
        title=title,
        text=text,
        links=links,
        meta_description=meta_desc,
        language=lang,
    )
