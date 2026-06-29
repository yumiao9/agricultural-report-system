"""Rule-based entity classification with LLM fallback."""

import re

from backend.services.llm_client import llm_chat_json
from backend.utils.logger import extractor_logger


# ── Rule-based Classification ────────────────────────────────────

_REGION_KEYWORDS = [
    "省", "市", "县", "乡", "镇", "村", "区",
    "产地", "产区", "之乡", "之都", "之县",
    "庄园", "农场", "牧场", "渔场", "林场",
    "产业园", "示范区", "开发区",
    "自治区", "自治州", "自治县",
]

_ENTERPRISE_KEYWORDS = [
    "集团", "公司", "股份", "有限", "企业",
    "厂", "社", "协会", "合作社",
    "有限公司", "总公司", "分公司",
    "高科", "科技", "种业", "实业",
]

_EQUIPMENT_KEYWORDS = [
    "机", "设备", "器", "仪", "车",
    "无人机", "拖拉机", "收割机", "播种机",
    "插秧机", "农机", "器具",
]

_PRODUCT_KEYWORDS = [
    "种植", "养殖", "栽培", "产量", "价格",
    "行情", "市场", "批发", "零售",
    "大米", "小麦", "玉米", "大豆", "水稻",
    "蔬菜", "水果", "生猪", "鸡蛋", "水产",
]

_COMMON_AGRICULTURAL_PRODUCTS = [
    # Grains
    "大米", "小麦", "玉米", "大豆", "水稻", "高粱", "小米", "糯米",
    "黑米", "荞麦", "燕麦", "薏米",
    # Fruits
    "苹果", "香蕉", "橙子", "葡萄", "西瓜", "草莓", "桃子", "梨",
    "猕猴桃", "芒果", "菠萝", "荔枝", "龙眼", "柚子", "柠檬",
    "樱桃", "杨梅", "枇杷", "石榴", "柿子", "山楂", "枣",
    "柑橘", "脐橙", "蜜橘", "砂糖橘",
    # Vegetables
    "白菜", "萝卜", "辣椒", "西红柿", "黄瓜", "茄子", "土豆", "大葱",
    "大蒜", "生姜", "豆角", "芹菜", "菠菜", "生菜", "韭菜",
    "花菜", "西兰花", "南瓜", "冬瓜", "丝瓜", "苦瓜", "莲藕",
    # Meat & Eggs
    "猪肉", "牛肉", "羊肉", "鸡肉", "鸭肉", "鹅肉",
    "鸡蛋", "鸭蛋", "鹌鹑蛋",
    # Aquatic
    "鲤鱼", "草鱼", "鲫鱼", "虾", "蟹", "贝", "海参", "鲍鱼",
    "带鱼", "鲈鱼", "三文鱼", "金枪鱼",
    # Cash crops
    "棉花", "茶叶", "花生", "油菜", "甘蔗", "甜菜", "烟草",
    "橡胶", "油茶", "核桃", "板栗",
    # Herbs / specialties
    "枸杞", "人参", "灵芝", "三七", "当归", "黄芪", "红枣",
    "铁观音", "龙井", "普洱", "大红袍", "碧螺春",
    # Other common terms
    "生猪", "仔猪", "种猪", "鸡苗", "鸭苗",
]


def _rule_based_classify(query: str) -> dict | None:
    """Attempt to classify the query using rules only.

    Returns None if rules are uncertain (LLM fallback needed).
    """
    q = query.strip()

    # Check for region: explicit location keywords
    for kw in _REGION_KEYWORDS:
        if kw in q:
            extractor_logger.info(f"Rule classified as region (matched '{kw}' in '{q}')")
            name = q
            for suffix in ["产区", "产地", "产业", "农业"]:
                if q.endswith(suffix):
                    name = q[: -len(suffix)].strip()
                    break
            return {
                "entity_type": "agricultural_region",
                "entity_name": name or q,
                "keywords": [q, f"{q} 农业", f"{q} 经济", f"{q} 特色产业"],
                "search_query_zh": f"{q} 农业 经济 数据 2025",
            }

    # Smart region detection: patterns like "寿光蔬菜产业", "烟台苹果产业"
    # Pattern: locationName(2-4 chars) + productName(2-4 chars) + 产业/农业
    region_industry = re.search(
        r'^(.{2,4})(.{2,4})(产业|农业|种植|养殖|产区)$', q
    )
    if region_industry:
        region_name = region_industry.group(1)
        rest = region_industry.group(2) + region_industry.group(3)
        # Don't match if the first part is itself a known product (e.g. "养猪产业" -> product)
        is_known_product_start = any(
            region_name == p[:len(region_name)]
            for p in _COMMON_AGRICULTURAL_PRODUCTS
            if len(p) >= len(region_name)
        )
        if not is_known_product_start:
            extractor_logger.info(f"Rule classified as region (matched pattern: {region_name} + '{rest}')")
            return {
                "entity_type": "agricultural_region",
                "entity_name": region_name,
                "keywords": [region_name, f"{region_name} 农业", q, f"{q} 数据"],
                "search_query_zh": f"{region_name} 农业 经济 特色产业 2025",
            }

    # Also match "X地/镇/乡/村"
    location_suffix = re.search(
        r'^(.{2,6}?)(市|县|区|镇|乡|村|地区|产地|之乡)(.{0,6})$', q
    )
    if location_suffix:
        region_name = location_suffix.group(1) + location_suffix.group(2)
        rest = location_suffix.group(3)
        extractor_logger.info(f"Rule classified as region (matched location suffix: {region_name})")
        return {
            "entity_type": "agricultural_region",
            "entity_name": region_name,
            "keywords": [region_name, f"{region_name} 农业", q, f"{q} 数据"],
            "search_query_zh": f"{region_name} 农业 经济 特色产业 2025",
        }

    # Check for enterprise
    for kw in _ENTERPRISE_KEYWORDS:
        if kw in q:
            extractor_logger.info(f"Rule classified as enterprise (matched '{kw}' in '{q}')")
            return {
                "entity_type": "agricultural_enterprise",
                "entity_name": q,
                "keywords": [q, f"{q} 营收", f"{q} 主营业务", f"{q} 财务数据"],
                "search_query_zh": f"{q} 企业 财务 营收 2025",
            }

    # Check for equipment
    for kw in _EQUIPMENT_KEYWORDS:
        if kw in q:
            extractor_logger.info(f"Rule classified as equipment (matched '{kw}' in '{q}')")
            return {
                "entity_type": "agricultural_equipment",
                "entity_name": q,
                "keywords": [q, f"{q} 参数 价格", f"{q} 品牌", f"{q} 评测"],
                "search_query_zh": f"{q} 参数 价格 评测 2025",
            }

    # Check for known agricultural products
    for product in _COMMON_AGRICULTURAL_PRODUCTS:
        if product in q:
            extractor_logger.info(f"Rule classified as product (matched known item '{product}' in '{q}')")
            return {
                "entity_type": "agricultural_product",
                "entity_name": q,
                "keywords": [q, f"{q} 产量 面积", f"{q} 价格 行情", f"{q} 进出口"],
                "search_query_zh": f"{q} 产量 价格 市场 2025",
            }

    # If query has agricultural keywords, treat as product
    for kw in _PRODUCT_KEYWORDS:
        if kw in q:
            extractor_logger.info(f"Rule classified as product (matched '{kw}' in '{q}')")
            return {
                "entity_type": "agricultural_product",
                "entity_name": q,
                "keywords": [q, f"{q} 行情", f"{q} 市场", f"{q} 数据"],
                "search_query_zh": f"{q} 行情 市场 数据 2025",
            }

    # Uncertain — fall through to LLM
    return None


# ── LLM-based Classification (fallback) ──────────────────────────

ENTITY_CLASSIFIER_SYSTEM = """你是一个农业领域专家。分析用户输入的查询，判断它属于以下哪一类：

1. agricultural_product (农产品) - 如：大豆、玉米、猪肉、苹果、小麦、水稻、棉花
2. agricultural_enterprise (农业企业) - 如：中粮集团、新希望六和、大北农、隆平高科、牧原股份
3. agricultural_equipment (农机设备) - 如：拖拉机、收割机、无人机植保、播种机、插秧机
4. agricultural_region (产地/乡村) - 如：寿光蔬菜之乡、五常大米产区、安溪铁观音、某省某县的乡村、某个农业县

返回JSON格式：
{
  "entity_type": "agricultural_product",
  "entity_name": "大豆",
  "keywords": ["大豆", "产量", "价格", "种植面积"],
  "search_query_zh": "大豆 产量 价格 种植面积 2025"
}

注意：
- entity_type 必须是 agricultural_product / agricultural_enterprise / agricultural_equipment / agricultural_region 之一
- 如果输入模糊，选择最可能的类型"""


async def _llm_classify(query: str) -> dict:
    """Fallback: classify using LLM."""
    extractor_logger.info(f"LLM classifying entity: {query}")
    messages = [
        {"role": "system", "content": ENTITY_CLASSIFIER_SYSTEM},
        {"role": "user", "content": query},
    ]
    try:
        result = await llm_chat_json(messages, temperature=0.1, max_tokens=500)
    except Exception as e:
        extractor_logger.warning(f"LLM classification failed: {e}, defaulting to product")
        result = {"entity_type": "agricultural_product", "entity_name": query,
                  "keywords": [query], "search_query_zh": query}
    return result


# ── Public API ────────────────────────────────────────────────────

async def classify_entity(query: str) -> dict:
    """Classify the user's query using rules first, then LLM fallback.

    Args:
        query: Raw user input (Chinese).

    Returns:
        dict with entity_type, entity_name, keywords, search_query_zh
    """
    # Step 1: Try rule-based (instant, no API call)
    result = _rule_based_classify(query)
    if result:
        extractor_logger.info(f"Rule-classified: {result['entity_type']} - {result['entity_name']}")
        return result

    # Step 2: Fallback to LLM
    result = await _llm_classify(query)

    # Validate
    valid_types = {"agricultural_product", "agricultural_enterprise", "agricultural_equipment", "agricultural_region"}
    if result.get("entity_type") not in valid_types:
        result["entity_type"] = "agricultural_product"

    extractor_logger.info(f"LLM-classified: {result['entity_type']} - {result['entity_name']}")
    return result
