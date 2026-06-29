"""LLM-based entity classification."""

from backend.services.llm_client import llm_chat_json
from backend.utils.logger import extractor_logger


ENTITY_CLASSIFIER_SYSTEM = """你是一个农业领域专家。分析用户输入的查询，判断它属于以下哪一类：

1. agricultural_product (农产品) - 如：大豆、玉米、猪肉、苹果、小麦、水稻、棉花
2. agricultural_enterprise (农业企业) - 如：中粮集团、新希望六和、大北农、隆平高科、牧原股份
3. agricultural_equipment (农机设备) - 如：拖拉机、收割机、无人机植保、播种机、插秧机
4. agricultural_region (产地/乡村) - 如：寿光蔬菜之乡、五常大米产区、安溪铁观音、某省某县的乡村、某个农业县

同时提取关键词和优化后的搜索查询。

返回JSON格式：
{
  "entity_type": "agricultural_product",
  "entity_name": "大豆",
  "keywords": ["大豆", "产量", "价格", "种植面积"],
  "search_query_zh": "大豆 产量 价格 种植面积 2024"
}

注意：
- entity_type 必须是 agricultural_product / agricultural_enterprise / agricultural_equipment / agricultural_region 之一
- search_query_zh 应当包含用于搜索引擎的最佳关键词组合
- 如果输入模糊，选择最可能的类型"""


async def classify_entity(query: str) -> dict:
    """Classify the user's query into an entity type and extract metadata.

    Args:
        query: Raw user input (Chinese).

    Returns:
        dict with entity_type, entity_name, keywords, search_query_zh
    """
    messages = [
        {"role": "system", "content": ENTITY_CLASSIFIER_SYSTEM},
        {"role": "user", "content": query},
    ]

    extractor_logger.info(f"Classifying entity: {query}")
    result = await llm_chat_json(messages, temperature=0.1, max_tokens=500)

    # Validate
    valid_types = {"agricultural_product", "agricultural_enterprise", "agricultural_equipment", "agricultural_region"}
    if result.get("entity_type") not in valid_types:
        extractor_logger.warning(f"Invalid entity_type '{result.get('entity_type')}', defaulting to agricultural_product")
        result["entity_type"] = "agricultural_product"

    extractor_logger.info(f"Classified as: {result.get('entity_type')} - {result.get('entity_name')}")
    return result
