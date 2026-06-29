# 农业报告产出系统 (Agricultural Report Generation System)

## 简介

基于 AI 的农业桌面调研报告自动生成系统。输入农产品名称、农业企业或农机设备名称，系统自动搜索公开网络信息，提取结构化数据，交叉验证后生成专业的研究报告。

### 核心特性

- **智能分类**: 自动识别输入类型（农产品/企业/农机）
- **多源搜索**: DuckDuckGo 免费搜索 + 可配 Bing/SerpAPI
- **数据提取**: LLM 从网页中提取定量数据（产量、价格、面积等）
- **交叉验证**: 多源数据比对，标注置信度
- **专业报告**: 结构化研究报告，每个数据点可溯源
- **实时进度**: SSE 推送研究进度
- **PDF 导出**: 报告可下载为 PDF
- **缓存机制**: 相同查询 7 天内即时返回

## 快速开始

### 1. 环境要求

- Python 3.11+
- DeepSeek API Key（注册地址：https://platform.deepseek.com）

### 2. 安装依赖

```bash
cd agricultural-report-system
pip install -r requirements.txt
```

### 3. 配置

复制 `.env.example` 为 `.env` 并填入 API Key：

```env
DEEPSEEK_API_KEY=sk-你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat
```

### 4. 启动

```bash
cd agricultural-report-system
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 使用

浏览器打开 `http://localhost:8000`，输入查询即可。

## 项目结构

```
agricultural-report-system/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理
│   ├── models/                 # 数据模型
│   │   ├── database.py         # 数据库引擎
│   │   ├── report.py           # ORM 模型
│   │   └── schemas.py          # Pydantic 验证
│   ├── routers/                # API 路由
│   │   ├── research.py         # POST /api/research (SSE)
│   │   ├── reports.py          # CRUD /api/reports, PDF
│   │   └── pages.py            # HTML 页面
│   ├── services/               # 业务逻辑
│   │   ├── orchestrator.py     # 核心调度器
│   │   ├── entity_classifier.py # 实体分类
│   │   ├── fetcher.py          # 网页抓取
│   │   ├── extractor.py        # 数据提取
│   │   ├── verifier.py         # 交叉验证
│   │   ├── report_generator.py # 报告合成
│   │   ├── citation.py         # 引用管理
│   │   ├── cache.py            # 缓存
│   │   ├── progress.py         # SSE 进度
│   │   ├── llm_client.py       # LLM 客户端
│   │   └── search/             # 搜索提供者
│   ├── templates/              # Jinja2 模板
│   │   ├── base.html
│   │   ├── index.html          # 首页
│   │   ├── report.html         # 报告页
│   │   └── history.html        # 历史页
│   ├── static/                 # 静态资源
│   └── utils/                  # 工具函数
├── data/                       # SQLite 数据目录
├── tests/                      # 测试
├── requirements.txt
├── .env.example
└── README.md
```

## 数据来源

系统搜索以下类型的公开数据源（取决于查询内容）：

**农产品**: 农业农村部、国家统计局、中国农业信息网、百度百科、USDA、FAO
**农业企业**: 公司官网、行业报告网站、企查查/天眼查公开页
**农机设备**: 制造商官网、农机购置补贴系统、行业评测

## API 文档

启动后访问 `http://localhost:8000/docs` 查看 Swagger 文档。

### 主要端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 首页 |
| POST | `/api/research` | 开始研究（SSE 流） |
| GET | `/api/reports` | 历史报告列表 |
| GET | `/api/reports/{id}` | 报告详情 |
| GET | `/api/reports/{id}/pdf` | 下载 PDF |
| GET | `/report/{id}` | 报告页面 |
| GET | `/history` | 历史页面 |
| GET | `/api/health` | 健康检查 |

## 可选配置

```env
# 高端 LLM 备选
ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_MODEL=claude-sonnet-4-20250514
REPORT_LLM=deepseek    # 可选 claude

# 搜索引擎备选
SERPAPI_API_KEY=xxx    # 付费 Google 搜索
SEARCH_BACKEND=duckduckgo  # duckduckgo / serpapi / bing

# 缓存
CACHE_TTL_HOURS=168    # 报告缓存时间（小时）
```

## 免责声明

本系统生成的报告基于公开网络数据自动合成，仅供参考，不构成投资建议或决策依据。数据可能存在时滞，请以官方最新发布为准。
