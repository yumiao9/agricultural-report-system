"""LLM-based structured data extraction from web page text."""

import asyncio
import json

from backend.services.llm_client import llm_chat, llm_chat_json
from backend.utils.logger import extractor_logger
from backend.utils.text_cleaning import truncate_text


DATA_EXTRACTION_SYSTEM = """你是一个农业数据提取专家。从给定的网页文本中提取关于某个实体的所有定量数据。

对于每个数据点，提取以下字段：
- indicator (string): 指标名称，如"年产量"、"种植面积"、"市场价格"、"出口量"
- value (number or null): 数值（如果可以转为数字，否则为null）
- value_text (string): 原始数值文本，如"2000万吨"、"约500万亩"
- unit (string or null): 单位，如"吨"、"万亩"、"元/公斤"
- year (string or null): 数据对应的年份，如"2024"、"2023年"
- source_sentence (string): 包含该数据的原始句子，必须完整原文引用

规则：
1. 只提取明确写出的数据，不要推断或编造任何数据！如果文本中没有明确写出，返回空数组 []
2. 每个数据点一行，以JSON对象表示
3. 如果网页中没有定量数据，返回空数组 []
4. 注意区分不同年份的数据
5. 提取价格数据时注意单位（元/斤 vs 元/公斤 vs 元/吨）
6. 提取产量数据时注意范围（全国 vs 某省 vs 某企业）
7. source_sentence 必须是网页原文中完整的句子，不得改写
8. 必须包含年份字段，如果文本中没有明确年份则设为null

以JSON格式返回：
{
  "data_points": [
    {
      "indicator": "年产量",
      "value": 2000,
      "value_text": "2000万吨",
      "unit": "万吨",
      "year": "2024",
      "source_sentence": "2024年全国大豆产量达到2000万吨，较上年增长5%。"
    }
  ]
}

重要：如果你的输出中包含了任何网页原文中没有明确写出的数据，将导致严重后果。宁可返回空数组，也绝不编造数据。"""


async def extract_data_from_text(
    text: str,
    entity_name: str,
    source_url: str = "",
) -> list[dict]:
    """Extract structured data points from a raw text.

    Args:
        text: Cleaned HTML text content.
        entity_name: The entity being researched.
        source_url: URL the text came from (for traceability).

    Returns:
        List of DataPoint dicts.
    """
    if not text or len(text) < 100:
        return []

    # Truncate to manageable size
    text_chunk = truncate_text(text, max_chars=6000)

    messages = [
        {"role": "system", "content": DATA_EXTRACTION_SYSTEM},
        {"role": "user", "content": f"""实体名称：{entity_name}
数据来源URL：{source_url}

网页文本内容：
---
{text_chunk}
---

请提取所有关于'{entity_name}'的定量数据。"""},
    ]

    try:
        result = await llm_chat_json(messages, temperature=0.1, max_tokens=3000)
        data_points = result.get("data_points", [])

        # Attach source URL
        for dp in data_points:
            dp["source_url"] = source_url

        extractor_logger.info(
            f"Extracted {len(data_points)} data points from {source_url[:80]}"
        )
        return data_points
    except Exception as e:
        extractor_logger.error(f"Data extraction failed for {source_url[:80]}: {e}")
        return []


async def extract_data_from_pages(
    pages: list[dict],
    entity_name: str,
    max_concurrent: int = 3,
) -> list[dict]:
    """Extract data from multiple fetched pages concurrently.

    Args:
        pages: List of dicts from fetcher.fetch_pages()
        entity_name: Entity name.
        max_concurrent: Max concurrent LLM extraction calls.

    Returns:
        Combined list of DataPoint dicts (deduplicated).
    """
    successful = [p for p in pages if p.get("fetch_success") and p.get("text_content")]

    if not successful:
        extractor_logger.warning("No successful page fetches to extract from")
        return []

    semaphore = asyncio.Semaphore(max_concurrent)

    async def extract_one(page: dict) -> list[dict]:
        async with semaphore:
            return await extract_data_from_text(
                text=page["text_content"],
                entity_name=entity_name,
                source_url=page["url"],
            )

    tasks = [extract_one(page) for page in successful]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Flatten and deduplicate
    all_points = []
    seen = set()
    for r in results:
        if isinstance(r, list):
            for dp in r:
                # Deduplicate by (indicator, year, value_text)
                key = (dp.get("indicator", ""), dp.get("year", ""), dp.get("value_text", ""))
                if key not in seen:
                    seen.add(key)
                    all_points.append(dp)

    extractor_logger.info(f"Total unique data points: {len(all_points)} from {len(successful)} pages")
    return all_points
