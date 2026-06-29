"""LLM-based report synthesis — generates structured markdown research reports."""

from backend.services.llm_client import llm_chat
from backend.utils.logger import llm_logger


# ── Report Templates ────────────────────────────────────────────

PRODUCT_REPORT_TEMPLATE = """## 报告摘要
> 对{entity_name}的产业发展现状、市场格局与趋势进行全景式梳理的核心结论。

## 1. 产品概述
### 1.1 基本信息
### 1.2 主要品种与产区
### 1.3 生长周期与季节性

## 2. 生产概况
### 2.1 国内产量与面积
### 2.2 主要产区分布
### 2.3 单产水平与变化趋势

## 3. 市场分析
### 3.1 供需格局
### 3.2 价格走势
### 3.3 主要消费渠道

## 4. 进出口数据
### 4.1 进口规模与来源国
### 4.2 出口规模与目的地
### 4.3 贸易政策影响

## 5. 相关政策
### 5.1 补贴政策
### 5.2 产业规划
### 5.3 贸易政策

## 6. 行业趋势
### 6.1 技术应用
### 6.2 消费变化
### 6.3 风险与机遇

## 数据汇总表
| 指标 | 数值 | 年份 | 来源 |
|------|------|------|------|

## 信息来源
（引用编号列表，由系统自动生成）

## 免责声明
本报告基于公开来源数据自动生成，仅供参考，不构成投资建议。数据可能存在时滞，请以官方最新发布为准。"""

ENTERPRISE_REPORT_TEMPLATE = """## 报告摘要
> 对{entity_name}的企业概况、经营状况与行业地位进行梳理的核心结论。

## 1. 企业概况
### 1.1 基本信息
### 1.2 股权结构
### 1.3 发展历程

## 2. 主营业务
### 2.1 产品与服务
### 2.2 业务模式
### 2.3 核心品牌

## 3. 经营数据
### 3.1 财务表现
### 3.2 产能规模
### 3.3 员工与组织

## 4. 市场地位
### 4.1 市场份额
### 4.2 竞争格局
### 4.3 行业排名

## 5. 发展动态
### 5.1 近期新闻
### 5.2 战略布局
### 5.3 风险提示

## 数据汇总表
| 指标 | 数值 | 年份 | 来源 |
|------|------|------|------|

## 信息来源
（引用编号列表，由系统自动生成）

## 免责声明
本报告基于公开来源数据自动生成，仅供参考，不构成投资建议。数据可能存在时滞，请以官方最新发布为准。"""

EQUIPMENT_REPORT_TEMPLATE = """## 报告摘要
> 对{entity_name}的技术特性、市场格局与应用评价进行梳理的核心结论。

## 1. 设备概述
### 1.1 定义与用途
### 1.2 分类与型号
### 1.3 关键特性

## 2. 技术参数
### 2.1 主要技术指标
### 2.2 智能化水平
### 2.3 国内外技术对比

## 3. 生产企业与品牌
### 3.1 主要生产商
### 3.2 品牌对比
### 3.3 市场份额

## 4. 市场价格
### 4.1 价格区间
### 4.2 补贴政策
### 4.3 购买渠道

## 5. 适用性与评价
### 5.1 适用场景
### 5.2 用户反馈
### 5.3 发展趋势

## 数据汇总表
| 指标 | 数值 | 年份 | 来源 |
|------|------|------|------|

## 信息来源
（引用编号列表，由系统自动生成）

## 免责声明
本报告基于公开来源数据自动生成，仅供参考，不构成投资建议。数据可能存在时滞，请以官方最新发布为准。"""

REGION_REPORT_TEMPLATE = """## 报告摘要
> 对{entity_name}的区域农业概况、特色产业与发展前景进行系统梳理的核心结论。

## 1. 区域概况
### 1.1 地理位置与自然条件
### 1.2 行政区划与人口
### 1.3 交通与基础设施

## 2. 农业经济
### 2.1 农业总产值与结构
### 2.2 主要农产品与产量
### 2.3 特色产业与地理标志产品

## 3. 重点产业
### 3.1 种植业
### 3.2 养殖业
### 3.3 农产品加工

## 4. 乡村振兴
### 4.1 政策扶持
### 4.2 重点项目
### 4.3 乡村旅游

## 5. 市场与贸易
### 5.1 主要销售渠道
### 5.2 品牌建设
### 5.3 电商发展

## 6. 发展前景
### 6.1 优势与机遇
### 6.2 挑战与对策
### 6.3 发展规划

## 数据汇总表
| 指标 | 数值 | 年份 | 来源 |
|------|------|------|------|

## 信息来源
（引用编号列表，由系统自动生成）

## 免责声明
本报告基于公开来源数据自动生成，仅供参考，不构成投资建议。数据可能存在时滞，请以官方最新发布为准。"""

TEMPLATES = {
    "agricultural_product": PRODUCT_REPORT_TEMPLATE,
    "agricultural_enterprise": ENTERPRISE_REPORT_TEMPLATE,
    "agricultural_equipment": EQUIPMENT_REPORT_TEMPLATE,
    "agricultural_region": REGION_REPORT_TEMPLATE,
}

# ── Synthesis Prompt ────────────────────────────────────────────

REPORT_SYNTHESIS_SYSTEM = """你是一位资深农业行业分析师，拥有20年中国农业产业研究经验。请根据以下收集到的数据，撰写一份关于{entity_name}的专业研究报告。

## 写作要求 - 必须严格遵守

1. **严格遵循报告模板结构**：按照提供的模板逐节撰写，不要跳过任何章节

2. **每个事实性陈述必须标注引用编号**：
   - 格式：2024年大豆产量达到2000万吨[1][3]
   - 引用编号对应下方"参考数据来源"中的编号
   - 如果某个数据点在多个来源中出现，列出所有相关引用
   - **绝对不允许出现没有引用标注的数据陈述**
   - 文中引用必须带方括号数字，如[1]、[2]、[1][3]

3. **数据溯源原则（最重要）**：
   - 每个数据点必须关联到具体的引用来源
   - 如果某个数据没有对应的引用编号，则不能写入报告
   - 不得写入任何没有明确来源的数据
   - 宁缺毋滥：没有数据支撑的章节填写"该数据暂未获取"

4. **语言风格**：
   - 专业、客观、精准
   - 类似券商行业研究报告风格
   - 使用数据说话，避免空泛描述
   - 全文使用中文

5. **数据使用原则**：
   - 优先使用多个来源交叉验证的数据
   - 如某数据仅有单一来源，注明"据单一来源数据..."
   - 如某方面数据完全缺失，在对应小节中明确说明"该数据暂未获取，待后续补充"
   - 不要编造任何数据！宁缺毋滥

6. **报告长度**：
   - 目标2000-4000字（中文）
   - 数据丰富的章节详写，数据不足的章节简写
   - 报告摘要控制在200-300字

7. **数据汇总表**：
   - 从提取的数据点中选择最重要的10-15项
   - 填入模板中的数据汇总表
   - 来源列填写引用编号，如[1]、[2]

8. **"参考资料"章节**：
   - 在报告最后列出完整的参考资料列表
   - 按[1][2][3]顺序排列
   - 每个条目包含：标题、URL、访问日期

## 参考数据来源

{data_sources_text}

## 提取的数据点

{data_points_text}

## 参考网页内容摘要

{context_text}
"""


async def generate_report_markdown(
    entity_name: str,
    entity_type: str,
    data_points: list[dict],
    fetched_pages: list[dict],
    citations: list[dict],
) -> str:
    """Generate a structured markdown research report.

    Args:
        entity_name: Name of the research subject.
        entity_type: One of agricultural_product / agricultural_enterprise / agricultural_equipment.
        data_points: Extracted DataPoint dicts.
        fetched_pages: Fetched page dicts (for context).
        citations: Citation dicts with ref_number, title, url.

    Returns:
        Complete markdown report text.
    """
    template = TEMPLATES.get(entity_type, PRODUCT_REPORT_TEMPLATE)
    template = template.format(entity_name=entity_name)

    # Build data sources text (citations) with full details
    sources_lines = []
    for c in citations:
        sources_lines.append(
            f"[{c['ref_number']}] {c.get('title', '未知标题')}\n"
            f"    URL: {c.get('url', '')}\n"
            f"    摘要: {c.get('snippet', '无')}\n"
            f"    访问日期: {c.get('access_date', '')}"
        )
    data_sources_text = "\n\n".join(sources_lines) if sources_lines else "暂无数据来源"

    # Build data points text
    dp_lines = []
    for i, dp in enumerate(data_points, 1):
        dp_lines.append(
            f"{i}. {dp.get('indicator', '未知指标')}: "
            f"{dp.get('value_text', dp.get('value', 'N/A'))} "
            f"({dp.get('year', '年份未知')}) "
            f"[来源: {dp.get('source_url', '未知')}]"
        )
    data_points_text = "\n".join(dp_lines) if dp_lines else "暂无提取到的数据点"

    # Build context from fetched pages
    context_parts = []
    for page in fetched_pages:
        if page.get("fetch_success") and page.get("text_content"):
            # Take first 1500 chars of each page as context
            snippet = page["text_content"][:1500]
            context_parts.append(
                f"来源: {page['url']}\n标题: {page.get('title', '未知')}\n内容摘要:\n{snippet}\n---"
            )
    context_text = "\n\n".join(context_parts[:8]) if context_parts else "暂无网页内容"

    # Build references lookup (URL -> ref_number)
    ref_lookup = {}
    for c in citations:
        ref_lookup[c["url"]] = str(c["ref_number"])

    # Annotate data_points with inline citations
    annotated_dps = []
    for dp in data_points:
        dp_source_url = dp.get("source_url", "")
        ref_nums = []
        for url, ref in ref_lookup.items():
            if dp_source_url and (url == dp_source_url or dp_source_url in url or url in dp_source_url):
                ref_nums.append(ref)
        inline_refs = f"[{']['.join(sorted(set(ref_nums), key=lambda x: int(x) if x.isdigit() else 0))}]" if ref_nums else ""
        value_text = dp.get("value_text", str(dp.get("value", "")))
        annotated_dps.append(f"- {dp.get('indicator', '')}: {value_text} ({dp.get('year', '')}) {inline_refs}")

    annotated_dps_text = "\n".join(annotated_dps) if annotated_dps else "暂无提取到的数据点"

    # Build user prompt
    user_prompt = f"""请为"{entity_name}"撰写一份完整的农业研究报告。

## 报告模板（必须遵循此结构）

{template}

## 注意事项（必读）
1. 每个事实性数据必须标注引用编号，如[1][2]
2. 缺乏数据的章节明确说明"该数据暂未获取"
3. 数据汇总表至少包含5项数据，来源列须写引用编号
4. 报告末尾必须包含"参考资料"章节，列出所有引用来源

## 已提取数据点（含来源标注）
{annotated_dps_text}"""

    messages = [
        {"role": "system", "content": REPORT_SYNTHESIS_SYSTEM.format(
            entity_name=entity_name,
            data_sources_text=data_sources_text,
            data_points_text=data_points_text,
            context_text=context_text,
        )},
        {"role": "user", "content": user_prompt},
    ]

    llm_logger.info(f"Generating report for {entity_name} ({entity_type})")
    llm_logger.info(f"Context: {len(data_points)} data points, {len(citations)} citations, {len(fetched_pages)} pages")

    try:
        markdown = await llm_chat(
            messages=messages,
            temperature=0.4,
            max_tokens=8192,
        )
        llm_logger.info(f"Report generated: {len(markdown)} chars")
        return markdown
    except Exception as e:
        llm_logger.error(f"Report generation failed: {e}")
        raise
