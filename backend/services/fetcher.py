"""Web page fetcher with HTML cleaning via httpx + BeautifulSoup4."""

import asyncio
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from backend.config import settings
from backend.utils.logger import fetcher_logger
from backend.utils.text_cleaning import clean_html_text, is_likely_navigation
from backend.utils.rate_limiter import DomainRateLimiter

# Rate limiter: 1 request per 2 seconds per domain
rate_limiter = DomainRateLimiter(default_rate=0.5)


async def fetch_page(
    url: str,
    timeout: float = 15.0,
    max_retries: int = 2,
) -> dict:
    """Fetch and clean a single web page.

    Returns:
        dict with keys: url, title, text_content, fetch_success, error_message
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }

    parsed = urlparse(url)
    domain = parsed.netloc or parsed.hostname or "unknown"

    # Rate limit per domain
    await rate_limiter.wait(domain)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
    ) as client:
        last_error = None
        for attempt in range(max_retries + 1):
            try:
                fetcher_logger.info(f"Fetching [{attempt+1}/{max_retries+1}]: {url[:100]}")
                resp = await client.get(url)
                resp.raise_for_status()

                # Try to detect encoding
                content_type = resp.headers.get("content-type", "")
                if "charset=" in content_type:
                    encoding = content_type.split("charset=")[-1].strip()
                else:
                    encoding = "utf-8"

                try:
                    html = resp.text
                except Exception:
                    html = resp.content.decode(encoding, errors="replace")

                # Parse with BeautifulSoup
                soup = BeautifulSoup(html, "lxml")

                # Extract title
                title = ""
                if soup.title:
                    title = soup.title.get_text(strip=True)

                # Remove non-content elements
                for tag in soup.find_all(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()

                # Remove common non-content classes/ids
                selectors_to_remove = [
                    ".sidebar", ".nav", ".footer", ".header", ".advertisement",
                    "#sidebar", "#nav", "#footer", "#header", ".comment",
                    ".menu", "#menu",
                ]
                for selector in selectors_to_remove:
                    try:
                        for el in soup.select(selector):
                            el.decompose()
                    except Exception:
                        pass

                # Extract body text
                body = soup.find("body")
                if body:
                    text = body.get_text(separator="\n", strip=True)
                else:
                    text = soup.get_text(separator="\n", strip=True)

                # Clean text
                text = clean_html_text(text)

                # Truncate to reasonable size (save full text, LLM will chunk)
                if len(text) > 50000:
                    text = text[:50000] + "\n\n[内容过长，已截断...]"

                fetcher_logger.info(f"Fetched {url[:80]}: {len(text)} chars, title='{title[:50]}'")
                return {
                    "url": url,
                    "title": title,
                    "text_content": text,
                    "fetch_success": True,
                    "error_message": None,
                }

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                if e.response.status_code in (403, 404, 410):
                    break  # Don't retry
            except httpx.TimeoutException:
                last_error = "Timeout"
            except Exception as e:
                last_error = str(e)[:200]

            if attempt < max_retries:
                delay = 2 ** attempt
                fetcher_logger.warning(f"Retry {url[:80]} in {delay}s: {last_error}")
                await asyncio.sleep(delay)

    fetcher_logger.error(f"Failed to fetch {url[:80]}: {last_error}")
    return {
        "url": url,
        "title": "",
        "text_content": "",
        "fetch_success": False,
        "error_message": last_error,
    }


async def fetch_pages(
    urls: list[str],
    max_concurrent: int = 5,
    timeout: float = 15.0,
) -> list[dict]:
    """Fetch multiple pages concurrently with concurrency limiting."""
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(url: str) -> dict:
        async with semaphore:
            return await fetch_page(url, timeout=timeout)

    tasks = [fetch_with_semaphore(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle exceptions
    output = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            output.append({
                "url": urls[i] if i < len(urls) else "unknown",
                "title": "",
                "text_content": "",
                "fetch_success": False,
                "error_message": str(r)[:200],
            })
        else:
            output.append(r)

    success_count = sum(1 for r in output if r["fetch_success"])
    fetcher_logger.info(f"fetch_pages: {success_count}/{len(urls)} succeeded")
    return output
