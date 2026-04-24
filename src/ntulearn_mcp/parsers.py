"""HTML body parsing utilities for Blackboard content items."""

from __future__ import annotations

from bs4 import BeautifulSoup


def extract_bbcswebdav_url(html_body: str) -> tuple[str | None, str | None]:
    """Parse a Blackboard content item's body HTML.

    Returns (url, filename) where url is the first bbcswebdav href found and
    filename is taken from the data-bbfile attribute when present.
    Returns (None, None) if no matching link is found.
    """
    if not html_body:
        return None, None

    soup = BeautifulSoup(html_body, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if "bbcswebdav" in href:
            filename = tag.get("data-bbfile") or tag.get_text(strip=True) or None
            # data-bbfile is sometimes a JSON-ish string like {"name":"file.pdf"}
            # try to unwrap it
            if filename and filename.startswith("{"):
                import json
                try:
                    parsed = json.loads(filename)
                    filename = (
                        parsed.get("linkName")
                        or parsed.get("displayName")
                        or parsed.get("name")
                        or parsed.get("filename")
                        or filename
                    )
                except (json.JSONDecodeError, AttributeError):
                    pass
            return href, filename or None

    return None, None


def extract_all_files(html_body: str) -> list[dict[str, str | None]]:
    """Return all bbcswebdav file links found in body HTML.

    Each entry: {"url": str, "filename": str | None, "link_text": str | None}
    """
    if not html_body:
        return []

    soup = BeautifulSoup(html_body, "html.parser")
    results: list[dict[str, str | None]] = []

    for tag in soup.find_all("a", href=True):
        href = tag["href"]
        if "bbcswebdav" in href:
            filename = tag.get("data-bbfile") or None
            if filename and filename.startswith("{"):
                import json
                try:
                    parsed = json.loads(filename)
                    filename = (
                        parsed.get("linkName")
                        or parsed.get("displayName")
                        or parsed.get("name")
                        or parsed.get("filename")
                        or filename
                    )
                except (json.JSONDecodeError, AttributeError):
                    pass
            results.append({
                "url": href,
                "filename": filename,
                "link_text": tag.get_text(strip=True) or None,
            })

    return results
