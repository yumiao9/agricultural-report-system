"""Regex-based data extraction - no LLM required, works within Vercel 10s limit."""

import re

_PATTERNS = [
    (r'((?:年)?总?\s*产量?)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[吨公斤斤担]|[吨公斤斤担]|亿斤))', '产量'),
    (r'((?:年产|总产|生产)量?)\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[吨公斤斤担]|[吨公斤斤担]|亿斤))', '产量'),
    (r'((?:年)?产量?)\s*(?:达到|突破|增至|为)\s*([\d.,]+\s*(?:万[吨公斤斤]|[吨公斤斤]))', '产量'),
    (r'((?:播种|种植|耕地|收获)?\s*面积)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[亩公顷]|[亩公顷]))', '面积'),
    (r'((?:市场|收购|批发|平均|均价)?\s*价格)\s*[:：]?\s*(?:为|约)?\s*([\d.,]+\s*元?\s*/\s*(?:[斤公斤吨]|千克))', '价格'),
    (r'(价格)\s*(?:.*?)([\d.,]+\s*元\s*/\s*(?:[斤公斤吨]|千克))', '价格'),
    (r'((?:单|亩)产)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:[斤公斤吨]\s*/\s*(?:亩|公顷))?)', '单产'),
    (r'((?:营收|产值|总收入|销售收入))\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万|亿|千亿)?\s*元)', '营收'),
    (r'((?:进口|出口)量)\s*[:：]?\s*(?:达到|为|约)?\s*([\d.,]+\s*(?:万[吨公斤]|[吨公斤]))', '贸易'),
    (r'((?:同比|环比)?\s*(?:增长|下降|减少|增加))\s*[:：]?\s*([\d.,]+\s*%?)', '变化率'),
    (r'(\S{2,8}?)\s*[:：]?\s*(?:达到|为|约|突破|增至)?\s*([\d.,]+\s*(?:万[吨公斤斤亩公顷元]|[吨公斤斤亩公顷元]))', '其他'),
]

_UNITS = {x for x in ['万吨', '吨', '公斤', '斤', '万亩', '亩', '万公顷', '公顷', '万元', '亿元', '元', '%']}

_YEAR_RE = re.compile(r'(\d{4})\s*年')


def _find_year(text: str, pos: int, window: int = 120) -> str | None:
    nearby = text[max(0, pos - window):pos + window + 200]
    years = _YEAR_RE.findall(nearby)
    if years:
        y = years[0]
        if 2018 <= int(y) <= 2026:
            return y
    return None


def _extract_unit(v: str) -> str:
    for u in sorted(_UNITS, key=len, reverse=True):
        if u in v:
            return u
    return ''


def extract_from_text(text: str, source_url: str = '') -> list[dict]:
    if not text or len(text) < 50:
        return []

    data_points = []
    seen = set()
    text_clean = text.replace('\n', ' ').replace('  ', ' ')

    for pattern, indicator in _PATTERNS:
        try:
            for match in re.finditer(pattern, text_clean):
                groups = match.groups()
                if len(groups) < 2:
                    continue
                label = groups[0].strip()
                value_text = groups[1].strip()
                if len(label) < 1 or len(value_text) < 2:
                    continue
                if not re.search(r'\d', value_text):
                    continue

                final_indicator = label if len(label) >= 2 else indicator
                position = match.start()
                year = _find_year(text, position)

                key = (final_indicator, value_text, year or '')
                if key in seen:
                    continue
                seen.add(key)

                num_match = re.search(r'([\d.,]+)', value_text)
                numeric = None
                if num_match:
                    try:
                        numeric = float(num_match.group(1).replace(',', ''))
                    except ValueError:
                        pass

                unit = _extract_unit(value_text)
                ctx_start = max(0, position - 40)
                ctx_end = min(len(text), position + len(value_text) + 80)
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
        except re.error as e:
            print(f"Regex error in pattern: {pattern[:60]}... {e}")
            continue

    return data_points


def extract_from_pages(pages: list[dict]) -> list[dict]:
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
