"""Template-based report generator — produces analytical reports without LLM calls."""

from collections import defaultdict
from datetime import datetime


def _classify_data_points(data_points: list[dict]) -> dict:
    """Classify data points into categories for analysis."""
    categories = defaultdict(list)
    for dp in data_points:
        ind = (dp.get("indicator") or "").lower()
        if any(k in ind for k in ["产量", "产值", "产出"]):
            categories["production"].append(dp)
        elif any(k in ind for k in ["面积", "耕地", "播种"]):
            categories["area"].append(dp)
        elif any(k in ind for k in ["价格", "市场价", "均价", "批发价"]):
            categories["price"].append(dp)
        elif any(k in ind for k in ["出口", "进口", "贸易"]):
            categories["trade"].append(dp)
        elif any(k in ind for k in ["营收", "收入", "利润", "财务"]):
            categories["financial"].append(dp)
        elif any(k in ind for k in ["补贴", "政策"]):
            categories["policy"].append(dp)
        elif any(k in ind for k in ["单产", "亩产"]):
            categories["yield"].append(dp)
        else:
            categories["other"].append(dp)
    return dict(categories)


def _build_data_table(data_points: list[dict]) -> str:
    """Build a data summary table."""
    if not data_points:
        return "暂无获取到定量数据"

    rows = ["| 指标 | 数值 | 年份 | 数据质量 |", "|------|------|------|---------|"]
    for dp in data_points[:15]:
        indicator = dp.get("indicator", "—")
        value = dp.get("value_text") or str(dp.get("value") or "—")
        year = dp.get("year") or "—"
        conf = dp.get("confidence", "medium")
        badge = {"high": "✅ 高", "medium": "📊 中", "low": "⚠️ 低"}.get(conf, "📊 中")
        rows.append(f"| {indicator} | {value} | {year} | {badge} |")

    return "\n".join(rows)


def _build_executive_summary(entity_name: str, data_points: list[dict],
                              citations: list[dict], categories: dict) -> str:
    """Build a concise executive summary with key findings."""
    n_data = len(data_points)
    n_sources = len(citations)
    n_categories = sum(1 for v in categories.values() if v)

    points = []

    if n_data == 0:
        return (f"针对“{entity_name}”的桌面调研已完成，检索到 {n_sources} 个信息来源。"
                "当前未从公开信息中提取到结构化定量数据，以下报告基于可获得的定性信息整理。")

    # Data richness
    points.append(f"本次调研共获取 **{n_data} 项** 结构化数据，覆盖 **{n_categories} 个** 维度"
                  f"（生产、价格、贸易等），来自 **{n_sources} 个** 独立信息来源。")

    # Multi-source verification
    verified = sum(1 for dp in data_points if dp.get("confidence") == "high")
    if verified > 0:
        points.append(f"其中 **{verified} 项** 数据经多个来源交叉验证，可信度较高。")

    # Production data
    prod = categories.get("production", [])
    if prod:
        latest = max(prod, key=lambda x: x.get("year") or "")
        if latest.get("value_text"):
            points.append(f"产量方面，{latest.get('year', '近期')}数据为 **{latest['value_text']}**。")

    # Price data
    price = categories.get("price", [])
    if price:
        latest_p = max(price, key=lambda x: x.get("year") or "")
        if latest_p.get("value_text"):
            points.append(f"市场价格方面，{latest_p.get('year', '近期')}数据为 **{latest_p['value_text']}**。")

    # Trade data
    trade = categories.get("trade", [])
    if trade:
        points.append(f"贸易方面，获取到 **{len(trade)} 项** 相关进出口数据。")

    return " ".join(points)


def _build_analysis_section(data_points: list[dict], categories: dict) -> str:
    """Build a market analysis section from available data."""
    parts = []

    if not data_points:
        return "本次调研未从公开信息中提取到可用于分析的定量数据。"

    prod = categories.get("production", [])
    area = categories.get("area", [])
    price = categories.get("price", [])
    trade = categories.get("trade", [])
    yield_d = categories.get("yield", [])

    # Production analysis
    if prod:
        parts.append("### 📈 生产分析\n")
        for dp in prod:
            year = dp.get("year", "某年")
            val = dp.get("value_text") or str(dp.get("value", ""))
            parts.append(f"- {year}：{val}")
            if dp.get("source_sentence"):
                parts.append(f"  > {dp['source_sentence'][:150]}")
        parts.append("")

    # Area analysis
    if area:
        parts.append("### 📐 面积/规模分析\n")
        for dp in area:
            year = dp.get("year", "某年")
            val = dp.get("value_text") or str(dp.get("value", ""))
            parts.append(f"- {year}：{val}")
        parts.append("")

    # Price analysis
    if price:
        parts.append("### 💰 价格分析\n")
        values = []
        for dp in price:
            year = dp.get("year", "某年")
            val = dp.get("value_text") or str(dp.get("value", ""))
            values.append((year, val, dp.get("source_url", "")))
            parts.append(f"- {year}：{val}")
        # Trend analysis if 2+ data points
        if len(values) >= 2:
            parts.append(f"\n> 趋势判断：获取到 {len(values)} 个时期的价格数据，可用于趋势分析。")
        parts.append("")

    # Trade analysis
    if trade:
        parts.append("### 🌐 贸易分析\n")
        for dp in trade:
            year = dp.get("year", "某年")
            val = dp.get("value_text") or str(dp.get("value", ""))
            parts.append(f"- {year}：{val}")
        parts.append("")

    if not parts:
        parts.append("当前获取的数据尚不足以进行深入分析。")

    return "\n".join(parts)


def _build_source_assessment(citations: list[dict]) -> str:
    """Evaluate the quality and diversity of sources."""
    if not citations:
        return "本次研究未获取到有效的信息来源。"

    domains = defaultdict(int)
    for c in citations:
        url = c.get("url", "")
        for domain in ["moa.gov.cn", "stats.gov.cn", "gov.cn", "baike.baidu.com",
                       "agri.cn", "xinhuanet.com", "people.com.cn", "cnki.net"]:
            if domain in url:
                domains[domain] += 1
                break
        else:
            domains["其他"] += 1

    lines = [f"共获取 **{len(citations)}** 个信息来源，来源分布如下："]
    for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
        emoji = {"moa.gov.cn": "🏛️", "stats.gov.cn": "📊", "gov.cn": "🏛️",
                 "baike.baidu.com": "📖", "agri.cn": "🌾", "xinhuanet.com": "📰",
                 "people.com.cn": "📰", "cnki.net": "🎓"}.get(domain, "🌐")
        lines.append(f"- {emoji} {domain}：{count} 条")

    has_official = any(d in str(citations) for d in ["moa.gov.cn", "stats.gov.cn", "gov.cn"])
    if has_official:
        lines.append("\n✅ 包含政府/官方数据源，信息权威性较好。")
    else:
        lines.append("\n⚠️ 未获取到官方政府数据源，建议结合官方渠道进一步验证。")

    return "\n".join(lines)


def _build_conclusions(entity_name: str, data_points: list[dict],
                        categories: dict) -> str:
    """Build analytical conclusions from available data."""
    parts = []

    if not data_points:
        return (f"受限于公开信息的可获得性，本次对“{entity_name}”的调研未能获取充分的量化数据。"
                "建议从以下渠道补充信息：\n"
                "- 农业农村部官网 (moa.gov.cn)\n"
                "- 国家统计局 (stats.gov.cn)\n"
                "- 行业白皮书及专业数据库\n"
                "- 企业年报（针对企业类查询）")

    n_prod = len(categories.get("production", []))
    n_price = len(categories.get("price", []))
    n_trade = len(categories.get("trade", []))

    # Data sufficiency assessment
    if n_prod >= 2:
        parts.append(f"📊 **产量数据较充分**：获取到 {n_prod} 项产量相关数据，可支撑生产规模分析。")
    elif n_prod == 1:
        parts.append(f"📊 **产量数据有限**：仅获取到 1 项产量数据，建议补充多年度数据以观察趋势。")
    else:
        parts.append("📊 **产量数据缺失**：未获取到明确的产量数据。")

    if n_price >= 2:
        parts.append(f"💰 **价格数据充分**：获取到 {n_price} 项价格数据，可支撑市场行情分析。")
    elif n_price == 1:
        parts.append("💰 **价格数据有限**：仅获取到 1 项价格数据。")
    else:
        parts.append("💰 **价格数据缺失**：未获取到明确的价格行情数据。")

    # Overall assessment
    total = len(data_points)
    if total >= 10:
        parts.append(f"\n✅ **总体评估**：数据丰富度较高（{total} 项），"
                     "可支撑一份中等深度的产业研究报告。")
    elif total >= 5:
        parts.append(f"\n📋 **总体评估**：数据基本可用（{total} 项），"
                     "建议结合行业通识补充分析。")
    else:
        parts.append(f"\n⚠️ **总体评估**：数据较为有限（{total} 项），"
                     "结论仅供参考，建议扩大信息检索范围。")

    return "\n\n".join(parts)


# ── Main entry point ─────────────────────────────────────────────

def generate_template_report(
    entity_name: str,
    entity_type: str,
    entity_type_label: str,
    data_points: list[dict],
    citations: list[dict],
) -> str:
    """Generate a complete research report using templates only (no LLM).

    Returns markdown string.
    """
    categories = _classify_data_points(data_points)

    # Build each section
    summary = _build_executive_summary(entity_name, data_points, citations, categories)
    analysis = _build_analysis_section(data_points, categories)
    data_table = _build_data_table(data_points)
    source_assessment = _build_source_assessment(citations)
    conclusions = _build_conclusions(entity_name, data_points, categories)

    now_str = datetime.now().strftime("%Y年%m月%d日")

    report = f"""# {entity_name} 桌面调研报告

> 生成日期：{now_str}  |  类型：{entity_type_label}  |  基于公开网络信息自动生成

---

## 一、核心结论

{summary}

---

## 二、数据详情

{data_table}

---

## 三、分析判断

{analysis}

---

## 四、信息来源评估

{source_assessment}

---

## 五、结论与建议

{conclusions}

---

## 六、参考资料

"""

    if citations:
        for c in citations:
            title = c.get("title", "未知标题")
            url = c.get("url", "")
            report += f"- [{c['ref_number']}] {title}\n  {url}\n"
    else:
        report += "暂无引用来源。\n"

    report += """

---

> **免责声明**：本报告基于公开网络信息自动生成，所有数据均标注来源链接。报告中分析判断由系统根据结构化数据自动生成，仅供参考，不构成投资或决策建议。数据可能存在时滞，请以官方最新发布为准。
"""

    return report
