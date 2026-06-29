"""Text cleaning utilities for scraped HTML content."""

import re


def clean_html_text(text: str) -> str:
    """Clean extracted HTML text: remove extra whitespace, normalize."""
    if not text:
        return ""

    # Replace multiple newlines with double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Replace multiple spaces (but not newlines)
    text = re.sub(r"[ \t]{2,}", " ", text)
    # Strip leading/trailing whitespace per line
    lines = [line.strip() for line in text.splitlines()]
    # Remove empty lines at start/end
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    # Remove lines that are too short and don't look like content
    lines = [l for l in lines if len(l) > 2 or l == ""]

    return "\n".join(lines)


def extract_tables(soup) -> list[dict]:
    """Extract HTML tables as list of dicts (headers + rows)."""
    tables = []
    for table in soup.find_all("table"):
        headers = []
        rows = []
        # Try to find headers
        thead = table.find("thead")
        if thead:
            headers = [th.get_text(strip=True) for th in thead.find_all("th")]
        if not headers:
            first_row = table.find("tr")
            if first_row:
                headers = [th.get_text(strip=True) for th in first_row.find_all(["th", "td"])]

        # Get data rows
        tbody = table.find("tbody") or table
        for tr in tbody.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
            if cells and any(c for c in cells):
                rows.append(cells)

        if rows:
            tables.append({"headers": headers, "rows": rows})

    return tables


def truncate_text(text: str, max_chars: int = 8000) -> str:
    """Truncate text to max_chars, trying to break at a sentence boundary."""
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    # Try to find the last sentence-ending punctuation
    for punct in ["。", "！", "？", ".", "!", "?", "\n\n"]:
        last_idx = truncated.rfind(punct)
        if last_idx > max_chars * 0.7:
            return truncated[:last_idx + len(punct)]

    return truncated


def is_likely_navigation(text: str) -> bool:
    """Heuristic: check if text block looks like navigation/footer."""
    if len(text) < 30:
        return True
    nav_keywords = ["登录", "注册", "首页", "关于我们", "联系我们", "版权", "©", "copyright"]
    if any(kw in text.lower() for kw in nav_keywords):
        # Only flag if the text is short (likely nav snippet)
        if len(text) < 200:
            return True
    return False
