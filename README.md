# A2A 智能体协作架构 POC

## 项目概述

这是一个面向旅行预订场景的 A2A POC。当前版本已经从“规则解析 + 固定路由”的原型，升级为“LLM 驱动的多智能体编排”架构：

- Orchestrator 使用 Gemini 解析用户意图、提取结构化参数、决定路由分支
- Flight Agent 和 Hotel Agent 使用 LLM + Tool 的模式调用本地查询工具
- 系统返回结构化方案结果，同时生成面向用户的自然语言摘要
- 前端和后端由同一个 FastAPI 进程统一提供

当前数据源仍是本地 mock 数据，适合做流程验证、Prompt 调优、路由实验和前端联调。

## 当前能力

- 支持中文自然语言输入
- 支持单程机票查询
- 支持往返机票 + 酒店组合查询
- 支持酒店单独查询（hotel_only）
- 支持“国家名 -> 多机场候选”匹配
- 支持多轮对话历史传入后端
- 支持 LLM 自动生成用户可读总结
- 支持通过 FastAPI 同时提供 API 和静态前端页面

示例：

- 帮我订 6 月 10 日从泰国飞往中国的机票
- 帮我预订机票和酒店，6 月 10 日从曼谷飞北京，6 月 14 日返回
- 我想 6 月中旬去上海，帮我看看机票和酒店

## 当前架构

### 1. Orchestrator

Orchestrator 是整个系统的入口，负责：

- 接收用户输入和历史对话
- 调用 Gemini 提取意图和参数
- 根据意图进行条件路由
- 聚合子智能体结果
- 生成自然语言总结

当前状态结构定义在 [agents/orchestrator.py](agents/orchestrator.py) 中，核心字段包括：

- `user_input`
- `chat_history`
- `parsed_params`
- `intent`
- `flight_options`
- `hotel_options`
- `combined_options`
- `llm_summary`

### 2. Flight Agent

Flight Agent 使用 ReAct Agent 调用 [tools/flight_search.py](tools/flight_search.py) 中的 `FlightSearchTool`。

输入参数由 LLM 解释后组织为结构化字段：

- `origin_candidates`
- `destination_candidates`
- `departure_date`
- `return_date`

这让系统可以处理：

- 城市名
- 机场代码
- 国家名到多机场候选映射

例如“泰国飞中国”会被解析为：

- `origin_candidates = ["BKK"]`
- `destination_candidates = ["PEK", "SHA", "HKG"]`

### 3. Hotel Agent

Hotel Agent 同样使用 ReAct Agent 调用 [tools/hotel_search.py](tools/hotel_search.py) 中的 `HotelSearchTool`。

工具按照以下条件过滤酒店：

- 目的地城市代码匹配
- 入住时间应在航班到达后的允许窗口内
- 退房时间应早于返程出发前的缓冲时间

### 4. 路由图

当前 LangGraph 条件路由逻辑如下：

```text
llm_parse_intent
   ├─ flight_only / flight_and_hotel -> call_flight
   │    ├─ flight_only -> llm_summarize
   │    └─ flight_and_hotel -> call_hotel -> llm_summarize
   ├─ hotel_only -> call_hotel
   └─ other -> llm_summarize
```

说明：`hotel_only` 已完成完整闭环：

- Orchestrator 会从 hotel-only 意图中提取 `hotel_city`、入住/退房日期
- 后端会合成酒店查询时间窗并调用 `hotel_agent`
- 前端和 CLI 会基于 `intent=hotel_only` 走酒店专用展示逻辑

## 技术栈

| 层次 | 选型 | 说明 |
|------|------|------|
| 编排层 | LangGraph | StateGraph + 条件路由 |
| LLM | Gemini（默认 `gemini-2.5-flash`，可通过 `GEMINI_MODEL` 配置） | 意图解析、Agent 工具调用、结果总结 |
| Tool 层 | LangChain Tool | 对 mock 航班/酒店数据做结构化查询 |
| 服务层 | FastAPI + asyncio | 提供 API 和前端静态页面 |
| 数据层 | PostgreSQL + SQLAlchemy | 初始化数据库与后续状态扩展 |
| 前端 | 静态 HTML | 通过 FastAPI 直接托管 |
| 配置 | python-dotenv | 加载 `.env` |

## 目录结构

```text
A2A_POC_Rui/
├─ main.py
├─ launcher.py
├─ cli.py
├─ README.md
├─ requirements.txt
├─ docker-compose.yml
├─ frontend/
│  ├─ poc.html
│  └─ test.html
├─ agents/
│  ├─ orchestrator.py
│  ├─ flight_agent.py
│  └─ hotel_agent.py
├─ tools/
│  ├─ flight_search.py
│  └─ hotel_search.py
├─ a2a/
│  ├─ protocol.py
│  └─ router.py
├─ db/
│  ├─ models.py
│  ├─ session.py
│  └─ state_store.py
└─ mock_data/
    ├─ flights.json
    └─ hotels.json
```

## 环境要求

- Python 3.10+ 推荐
- Docker / Docker Compose
- Gemini API Key

说明：当前环境在 Python 3.9 下也可能运行，但 Google 相关依赖会给出版本告警，建议升级到 3.10 或更高版本。

## 安装与启动

### 1. 创建并激活虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建或编辑 `.env`：

```env
DATABASE_URL=postgresql://a2a_user:a2a_password@localhost:5432/a2a_poc
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### 4. 启动数据库

```bash
docker-compose up -d
```

### 5. 启动服务

```bash
python3 main.py
```

启动成功后：

- API: `http://localhost:8000`
- 前端页面: `http://localhost:8000/poc.html`
- 测试页: `http://localhost:8000/test.html`

## API 说明

### POST `/chat`

请求体：

```json
{
   "user_input": "帮我预订机票和酒店，6月10日从曼谷飞北京，6月14日返回",
   "chat_history": [
      {
         "role": "user",
         "content": "我想去中国出差"
      },
      {
         "role": "assistant",
         "content": "请告诉我出发地和日期。"
      }
   ]
}
```

响应体：

```json
{
   "combined_options": [
      {
         "outbound": {},
         "return": {},
         "hotel": {}
      }
   ],
   "llm_summary": "共找到 3 个较合适的方案，优先推荐上午出发的组合，您可以继续让我按价格或时间排序。",
   "intent": "flight_and_hotel"
}
```

字段说明：

- `combined_options`: 结构化方案数据，供前端渲染
- `llm_summary`: LLM 生成的摘要，供聊天 UI 或 CLI 直接展示
- `intent`: 当前识别的意图类型（`flight_only` / `flight_and_hotel` / `hotel_only` / `other`）

## CLI 使用

当前 CLI 也已经接入多轮对话历史和 LLM 总结。

典型流程：

```text
> 帮我订 6 月 10 日从泰国飞往中国的机票
[正在为您搜索方案...]
已为您找到几条从曼谷前往中国主要城市的航班，包含北京、上海和香港方向。您可以继续说“只看最便宜的”或指定目的地城市。

── 方案清单 ──
方案 1: TG115 2025-06-10 BKK→PEK ¥380
方案 2: FM210 2025-06-10 BKK→SHA ¥360
方案 3: CX702 2025-06-10 BKK→HKG ¥340
```

## Mock 数据

当前 mock 数据已扩充，覆盖：

- 新加坡、上海、北京、香港、曼谷、旧金山
- 城市与国家混合表达
- 单程、往返、多日期组合
- 多城市酒店库存

数据文件：

- [mock_data/flights.json](mock_data/flights.json)
- [mock_data/hotels.json](mock_data/hotels.json)

## 当前限制

以下内容需要明确：

- 当前仍使用本地 mock 数据，不连接真实航司或酒店供应商
- LLM 意图解析存在 Prompt 约束，不是无限泛化的开放域旅行助手
- 数据库存储目前只完成初始化，尚未把完整会话/订单持久化打通
- 尚未实现真正的“一键启动脚本”，当前仍需分别启动数据库和应用

