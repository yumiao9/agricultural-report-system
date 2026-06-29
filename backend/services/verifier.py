"""Cross-reference verification and confidence scoring for data points."""

from collections import defaultdict

from backend.utils.logger import extractor_logger


def _normalize_indicator(indicator: str) -> str:
    """Normalize indicator names for grouping."""
    synonyms = {
        "产量": ["产量", "年产量", "总产量", "生产量"],
        "种植面积": ["种植面积", "播种面积", "面积", "耕地面积"],
        "价格": ["价格", "市场价", "均价", "平均价格", "收购价", "批发价"],
        "单产": ["单产", "亩产", "单位产量", "每公顷产量"],
        "进口量": ["进口量", "进口数量", "进口"],
        "出口量": ["出口量", "出口数量", "出口"],
        "产值": ["产值", "总产值", "市场规模"],
        "企业营收": ["营收", "营业收入", "收入", "销售额"],
        "市场份额": ["市场份额", "市场占有率", "占有率"],
        "补贴": ["补贴", "补贴金额", "农机补贴"],
    }

    for canonical, aliases in synonyms.items():
        if any(a in indicator for a in aliases):
            return canonical
    return indicator


def _parse_value(value_text: str) -> float | None:
    """Try to parse a value from text like '2000万吨' -> 2000."""
    import re

    if not value_text:
        return None

    # Remove Chinese units and commas
    cleaned = re.sub(r"[^\d.]", "", str(value_text).replace(",", "").replace("，", ""))
    try:
        return float(cleaned)
    except ValueError:
        return None


async def verify_data_points(data_points: list[dict]) -> list[dict]:
    """Cross-verify data points and assign confidence scores.

    Rules:
    - high: 2+ independent sources agree (within 30% tolerance)
    - medium: Single source, or 2+ sources with moderate disagreement
    - low: Sources conflict by >50%, or only weak evidence

    Args:
        data_points: List of DataPoint dicts with source_url.

    Returns:
        DataPoints with confidence field added.
    """
    if not data_points:
        return []

    # Group by normalized indicator
    groups = defaultdict(list)
    for dp in data_points:
        indicator = dp.get("indicator", "")
        norm = _normalize_indicator(indicator)
        groups[norm].append(dp)

    verified = []
    for norm_indicator, group in groups.items():
        n = len(group)

        if n >= 2:
            # Check agreement between sources
            values = []
            for dp in group:
                v = dp.get("value")
                if v is None:
                    v = _parse_value(dp.get("value_text", ""))
                if v is not None and v > 0:
                    values.append(v)

            if len(values) >= 2:
                max_v = max(values)
                min_v = min(values)
                spread = (max_v - min_v) / max_v if max_v > 0 else 0

                if spread <= 0.3:
                    confidence = "high"
                elif spread <= 0.5:
                    confidence = "medium"
                else:
                    confidence = "low"
            else:
                # Multiple sources but can't parse values → medium
                confidence = "medium"
        else:
            confidence = "medium"  # Single source

        # Assign confidence
        for dp in group:
            dp["confidence"] = confidence

        verified.extend(group)

    # Summary
    from collections import Counter
    counts = Counter(dp.get("confidence", "medium") for dp in verified)
    extractor_logger.info(
        f"Verification complete: {len(verified)} data points "
        f"(high={counts.get('high',0)}, medium={counts.get('medium',0)}, low={counts.get('low',0)})"
    )

    return verified
