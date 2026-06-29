"""Citation manager — tracks sources and formats references."""

from datetime import datetime, timezone


def build_citations(search_results: list, fetched_pages: list[dict]) -> list[dict]:
    """Build a citation list from search results and fetched pages.

    Args:
        search_results: List of SearchResult objects.
        fetched_pages: List of fetched page dicts.

    Returns:
        List of citation dicts with ref_number, title, url, snippet, access_date.
    """
    citations = []
    seen_urls = set()
    ref_num = 0

    # First add search results (they may have snippets)
    for sr in search_results:
        url = getattr(sr, "url", sr.get("url", "")) if isinstance(sr, dict) else sr.url
        title = getattr(sr, "title", sr.get("title", "")) if isinstance(sr, dict) else sr.title
        snippet = getattr(sr, "snippet", sr.get("snippet", "")) if isinstance(sr, dict) else sr.snippet

        if url and url not in seen_urls:
            ref_num += 1
            seen_urls.add(url)
            citations.append({
                "ref_number": ref_num,
                "title": title,
                "url": url,
                "snippet": snippet,
                "access_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })

    # Then add fetched pages that weren't in search results
    for page in fetched_pages:
        url = page.get("url", "")
        if url and url not in seen_urls and page.get("fetch_success"):
            ref_num += 1
            seen_urls.add(url)
            citations.append({
                "ref_number": ref_num,
                "title": page.get("title", ""),
                "url": url,
                "snippet": "",
                "access_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            })

    return citations


def format_citation_gbt7714(citation: dict) -> str:
    """Format a citation in GB/T 7714 style (Chinese academic standard).

    Format: [N] Author. Title[EB/OL]. (date)[access date]. URL
    """
    ref = citation["ref_number"]
    title = citation.get("title", "未知标题")
    url = citation.get("url", "")
    access_date = citation.get("access_date", "")

    # Online resource format
    return f"[{ref}] {title}[EB/OL]. ({access_date})[{access_date}]. {url}"


def format_references_section(citations: list[dict]) -> str:
    """Generate the full references section in markdown."""
    if not citations:
        return "暂无引用来源"

    lines = []
    for c in sorted(citations, key=lambda x: x["ref_number"]):
        lines.append(format_citation_gbt7714(c))

    return "\n\n".join(lines)


def build_citations_text(citations: list[dict]) -> str:
    """Build a formatted references section text for embedding in reports."""
    if not citations:
        return "本次研究未获取到有效的引用来源。"

    parts = ["## 参考资料"]
    for c in sorted(citations, key=lambda x: x["ref_number"]):
        title = c.get("title", "未知标题")
        url = c.get("url", "")
        snippet = c.get("snippet", "")
        access_date = c.get("access_date", "")

        entry = f"[{c['ref_number']}] {title}"
        if snippet:
            entry += f"\n    > {snippet[:150]}"
        entry += f"\n    链接: {url}"
        entry += f"\n    访问日期: {access_date}"
        parts.append(entry)

    return "\n\n".join(parts)


def format_inline_citation(data_point: dict, citations_lookup: dict) -> str:
    """Format a data point value with inline source citation.

    Args:
        data_point: DataPoint dict with source_url.
        citations_lookup: Dict mapping URL -> ref_number.

    Returns:
        Formatted string like "2000万吨[1][3]"
    """
    value_text = data_point.get("value_text", str(data_point.get("value", "")))
    source_url = data_point.get("source_url", "")

    ref_nums = []
    for url, ref in citations_lookup.items():
        if source_url and (url == source_url or url in source_url or source_url in url):
            ref_nums.append(str(ref))

    if ref_nums:
        return f"{value_text}[{']['.join(sorted(set(ref_nums), key=int))}]"
    return value_text
