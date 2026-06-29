"""Regex-based data extraction — no LLM required, works within Vercel 10s limit."""

import re

# Patterns for Chinese agricultural data
_PATTERNS = [
    # (regex, indicator_label)
    # Production
    (r'((?:年)?总?\s*产量?)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[吨公斤斤担]|[吨公斤斤担]|亿斤)))', '产量'),
    (r'((?:年产|总产|生产)量?)\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[吨公斤斤担]|[吨公斤斤担]|亿斤)))', '产量'),
    (r'((?:年)?产量?)\s*(?:达到|突破|增至|为)\s*([\d.,]+\s*(?:万[吨公斤斤]|[吨公斤斤])))', '产量'),
    # Area
    (r'((?:播种|种植|耕地|收获)?\s*面积)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[亩公顷平方米]|[亩公顷])))', '面积'),
    (r'((?:种植|播种)面积)\s*(?:达到|为)\s*([\d.,]+\s*(?:万[亩公顷]|[亩公顷])))', '面积'),
    # Price
    (r'((?:市场|收购|批发|平均|均价)?\s*价格)\s*[:：]?\s*(?:为|约)?\s*([\d.,]+\s*元?\s*/\s*(?:[斤公斤吨]|千克))', '价格'),
    (r'(价格)\s*(?:.*?)([\d.,]+\s*元\s*/\s*(?:[斤公斤吨]|千克))', '价格'),
    # Yield
    (r'((?:单|亩)产)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:[斤公斤吨]\s*/\s*(?:亩|公顷))?)', '单产'),
    # Revenue/Value
    (r'((?:营收|产值|总收入|销售收入))\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万|亿|千亿)?\s*元)', '营收'),
    # Trade
    (r'((?:进口|出口)量)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[吨公斤]|[吨公斤]))', '贸易'),
    # Growth rate
    (r'((?:同比|环比)?\s*(?:增长|下降|减少|增加))\s*[:：]?\s*([\d.,]+\s*%?)', '变化率'),
    # General: any number followed by common units in agriculture context
    (r'(?:(\S{2,8}?))\s*[:：]?\s*(?:达到|为|约|突破|增至)?\s*([\d.,]+\s*(?:万[吨公斤斤亩公顷元]|[吨公斤斤亩公顷元])))', '其他'),
]

# Common agricultural units  
_UNITS = {
    '吨': '吨', '万吨': '万吨', '公斤': '公斤', '斤': '斤',
    '亩': '亩', '万亩': '万亩', '公顷': '公顷', '万公顷': '万公顷',
    '元': '元', '万元': '万元', '亿元': '亿元',
    '%': '%', '千克': '公斤',
}

# Patterns to find year context
_YEAR_RE = re.compile(r'(\d{4})\s*年')


def _find_year(text: str, pos: int, window: int = 100) -> str | None:
    """Find the nearest year mention near a position in text."""
    # Look for 2020-2026 year patterns
    nearby = text[max(0, pos - window):pos + window + 200]
    years = _YEAR_RE.findall(nearby)
    if years:
        return years[0]
    return None


def _extract_unit(value_text: str) -> str:
    """Extract unit from value text."""
    for unit in sorted(_UNITS, key=len, reverse=True):
        if unit in value_text:
            return _UNITS[unit]
    return ''


def extract_from_text(text: str, source_url: str = '') -> list[dict]:
    """Extract quantitative data points from text using regex.

    Args:
        text: Page text content.
        source_url: Source URL for tracking.

    Returns:
        List of data point dicts.
    """
    if not text or len(text) < 50:
        return []

    data_points = []
    seen = set()
    text_clean = text.replace('\n', ' ').replace('  ', ' ')

    for pattern, indicator in _PATTERNS:
        for match in re.finditer(pattern, text_clean):
            groups = match.groups()
            if len(groups) < 2:
                continue

            label = groups[0].strip()
            value_text = groups[1].strip()

            # Skip if label or value is too short
            if len(label) < 1 or len(value_text) < 2:
                continue

            # Skip if value doesn't have a number
            if not re.search(r'\d', value_text):
                continue

            # Use matched label if it's descriptive enough
            if len(label) >= 2:
                final_indicator = label
            else:
                final_indicator = indicator

            position = match.start()
            year = _find_year(text, position)
            unit = _extract_unit(value_text)

            # Deduplicate
            key = (final_indicator, value_text, year or '')
            if key in seen:
                continue
            seen.add(key)

            # Try to parse numeric value
            numeric = None
            num_match = re.search(r'([\d.,]+)', value_text)
            if num_match:
                try:
                    numeric = float(num_match.group(1).replace(',', ''))
                except ValueError:
                    pass

            # Get context sentence
            ctx_start = max(0, position - 40)
            ctx_end = min(len(text), position + len(value_text) + 60)
            source_sentence = text[ctx_start:ctx_end].strip()

            data_points.append({
                'indicator': final_indicator,
                'value': numeric,
                'value_text': value_text,
                'unit': unit,
                'year': year or '',
                'source_url': source_url,
                'source_sentence': source_sentence,
                'confidence': 'medium',
            })

    return data_points


def extract_from_pages(pages: list[dict]) -> list[dict]:
    """Extract data from multiple pages using regex.

    Args:
        pages: List of fetched page dicts.

    Returns:
        Combined deduplicated data points.
    """
    all_points = []
    seen = set()

    for page in pages:
        if not page.get('fetch_success') or not page.get('text_content'):
            continue
        url = page.get('url', '')
        points = extract_from_text(page['text_content'], source_url=url)
        for p in points:
            key = (p['indicator'], p['value_text'], p.get('year', ''))
            if key not in seen:
                seen.add(key)
                all_points.append(p)

    return all_points
