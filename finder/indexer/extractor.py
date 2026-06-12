"""Clean text extraction from HTML — removes boilerplate, nav, footer, etc."""

from typing import Optional

from finder.crawler.parser import parse_html


def extract_clean_text(html: str, url: str) -> dict:
    """
    Extract clean article/content text from HTML.
    
    Uses trafilatura for main content extraction (best at removing
    boilerplate like navbars, footers, sidebars, ads). Falls back
    to BeautifulSoup basic extraction if trafilatura fails.
    
    Args:
        html: Raw HTML string.
        url: The page URL (used for relative link resolution).
    
    Returns:
        Dict with 'title', 'text', 'url' keys.
    """
    title = ""
    text = ""

    # Try trafilatura first (best at content extraction)
    try:
        import trafilatura
        result = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            favor_precision=True,
        )
        if result and len(result.strip()) > 50:
            text = result.strip()

        # Get metadata for title
        metadata = trafilatura.extract_metadata(html, url=url)
        if metadata and metadata.title:
            title = metadata.title
    except Exception:
        pass

    # Fallback to BeautifulSoup extraction
    if not text:
        try:
            parsed = parse_html(html, url)
            text = parsed.text
            if not title:
                title = parsed.title
        except Exception:
            pass

    # If still no title, try basic extraction
    if not title:
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            title_tag = soup.find("title")
            if title_tag and title_tag.string:
                title = title_tag.string.strip()
        except Exception:
            pass

    return {
        "title": title or "Untitled",
        "text": text,
        "url": url,
    }
