# A2A 智能体协作架构完整设计方案

## POC 技术方案文档

**A2A 智能体协作架构**  
**完整设计方案**

机票与酒店预订场景 · LangChain / LangGraph / A2A 协议 · PostgreSQL 状态持久化

- 版本 v1.1（含三项架构更新）
- 本地一键启动
- 自然语言交互

## 01 技术栈选型

| 层次       | 选型                  | 说明 |
|------------|-----------------------|------|
| 智能体框架 | LangGraph<br/>StateGraph 定义决策流 | 每个智能体内部用 `StateGraph` 描述节点与状态转移，支持条件边、循环和并发执行 |
| 工具链     | LangChain<br/>Tool 封装 + LLM 调用 | 将 Mock 数据查询封装为 LangChain Tool，意图解析与自然语言生成通过 LLM 完成 |
| 通信协议   | A2A Protocol<br/>Google 开源规范 | 智能体暴露 `AgentCard`，通过 Task / Message 结构收发指令。POC 中以进程内异步调用模拟，保留完整协议语义 |
| 服务框架   | FastAPI + asyncio<br/>单进程统一管理 | 三个智能体在同一 asyncio 事件循环中运行，`launcher.py` 统一调度，无需分别启动 |
| 状态持久化 | PostgreSQL<br/>SQLAlchemy ORM | LangGraph checkpointer 对接 PG，每个节点执行后自动快照；A2A 消息全量写入，支持链路回溯 |
| 用户交互   | 自然语言 CLI<br/>readline 终端循环 | 直接在终端输入中文，协调智能体首节点负责解析意图，对用户完全透明 |
| 本地数据   | Mock JSON<br/>模拟航班 / 酒店数据 | 无需真实 API，本地静态数据覆盖新加坡↔上海航班时刻与上海酒店库存 |
| 基础设施 | Docker Compose<br/>一行拉起 PostgreSQL | `docker-compose up -d` 拉起数据库，`python main.py` 启动全部服务 |

## 02 智能体角色设计

### 协调智能体 (Orchestrator)
- 内部路由 · 主入口
- 接收自然语言输入
- LLM 解析意图与参数
- 通过 A2A 下发任务
- 聚合结果 + 时间校验
- 格式化输出返回用户
- 写入 sessions 表快照

### 机票智能体 (Flight Agent)
- A2A 内部端点
- 实现 AgentCard 规范
- 接收出发 / 目的地 / 日期
- 调用 search_flights Tool
- 返回 4–5 个航班方案
- 附带起飞 / 到达时刻
- 写入 agent_tasks 表

### 酒店智能体 (Hotel Agent)
- A2A 内部端点
- 实现 AgentCard 规范
- 接收到达时间列表
- 调用 search_hotels Tool
- 入住 ≥ 到达 + 2h 过滤
- 退房与返程时间对齐
- 写入 agent_tasks 表

## 03 项目目录结构

```
a2a-poc/
├─ main.py                    # 唯一入口：初始化 DB → 启动 launcher → 进入 CLI
├─ cli.py                     # readline 自然语言交互循环
├─ launcher.py                # asyncio 统一启动三个智能体
├─ agents/
│  ├─ orchestrator.py         # LangGraph StateGraph · 任务路由
│  ├─ flight_agent.py         # 机票智能体 LangGraph + Tool
│  └─ hotel_agent.py          # 酒店智能体 LangGraph + Tool
├─ a2a/
│  ├─ protocol.py             # Task / Message / AgentCard 数据结构
│  └─ router.py               # 进程内消息路由（替代 HTTP）
├─ db/
│  ├─ models.py               # SQLAlchemy 表定义
│  ├─ session.py              # PostgreSQL 连接池
│  └─ state_store.py          # 智能体状态读写封装
├─ tools/
│  ├─ flight_search.py        # Mock 航班查询 Tool
│  └─ hotel_search.py         # Mock 酒店查询 Tool（含时间过滤）
├─ mock_data/
│  ├─ flights.json
│  └─ hotels.json
├─ .env                       # DATABASE_URL · LLM API Key
└─ docker-compose.yml         # PostgreSQL 容器
```

## 04 PostgreSQL 数据表设计

三张表覆盖完整的 A2A 链路记录，支持任意时间点回溯对话状态与消息流转。

### sessions
- id: UUID PK
- user_input: TEXT
- graph_state: JSONB
- status: VARCHAR
- created_at: TIMESTAMPTZ
- updated_at: TIMESTAMPTZ

### agent_tasks
- id: UUID PK
- session_id: UUID FK
- sender: VARCHAR
- receiver: VARCHAR
- task_payload: JSONB
- status: VARCHAR

### results
- id: UUID PK
- session_id: UUID FK
- flight_options: JSONB
- hotel_options: JSONB
- combined: JSONB
- selected: JSONB

## 05 完整交互流程

1. **用户 · CLI**  
   终端输入自然语言请求  
   例：帮我预订机票和酒店，5月1日从新加坡飞上海，5月4日返回

2. **协调智能体 · 意图解析节点**  
   LLM 提取结构化参数，写入 sessions 表  
   解析出：出发地、目的地、出发日期、返回日期 → 存入 graph_state

3. **协调智能体 → 机票智能体**  
   发送 A2A Task，写入 agent_tasks 表（status: pending）  
   携带参数：origin=SIN · destination=SHA · date=2025-05-01 / 2025-05-04

4. **机票智能体 · 搜索节点**  
   调用 search_flights Tool，返回 4–5 个往返航班方案  
   每条包含：航班号 · 起飞时间 · 到达时间 · 价格 → task status: done

5. **协调智能体 → 酒店智能体**  
   携带航班到达时间列表，发送 A2A Task  
   参数：arrive_times=[...] · depart_times=[...] · checkin_window_hours=3

6. **酒店智能体 · 匹配节点**  
   按时间窗口过滤，返回与每个航班匹配的酒店方案  
   入住时间 ≥ 到达时间 + 2h · 退房时间 ≤ 返程起飞 − 2h

7. **协调智能体 · 聚合 + 校验节点**  
   合并方案，剔除时间冲突组合，写入 results 表  
   生成 4–5 组完整行程方案（每组含去程 + 返程 + 酒店）

8. **用户 · CLI**  
   阅读方案，以自然语言选择或追问  
   例：我选第2组 / 有没有更便宜的酒店 / 确认预订

## 06 时间合理性校验规则

协调智能体聚合阶段对每一组航班 + 酒店组合执行以下判断，不通过则过滤，不呈现给用户。

### ✓ 合规条件
- 入住时间 ≥ 到达上海时间 + 2 小时
- 退房时间 ≤ 返程起飞时间 − 2 小时
- 入住日期 = 抵达当天（不可提前）
- 退房日期 = 返程当天

### ✗ 过滤条件
- 入住时间早于到达时间
- 入住日期早于 5 月 1 日
- 退房时间与返程冲突（时间过近）
- 住宿日期与航班日期不匹配

## 07 A2A 消息结构示例

协调智能体下发给酒店智能体的 A2A Task，携带来自机票智能体的到达时间列表：

```json
// 协调智能体 → 酒店智能体
{
  "id": "task-hotel-001",
  "sender": "orchestrator",
  "receiver": "hotel_agent",
  "status": "pending",
  "message": {
    "role": "user",
    "parts": [{
      "text": "请搜索上海酒店",
      "metadata": {
        "arrive_times": ["2025-05-01T09:30:00+08:00", "2025-05-01T13:00:00+08:00"],
        "depart_times": ["2025-05-04T08:00:00+08:00", "2025-05-04T11:30:00+08:00"],
        "checkin_window_hours": 3,
        "checkout_buffer_hours": 2
      }
    }]
  }
}
```

## 08 启动与交互方式

```
# 第一步：拉起 PostgreSQL
$ docker-compose up -d
  ✓ postgres container started on port 5432

# 第二步：启动所有智能体 + 进入对话
$ python main.py
  ✓ DB initialized
  ✓ Orchestrator agent ready
  ✓ Flight agent ready
  ✓ Hotel agent ready

> 帮我预订机票和酒店，5月1日从新加坡飞上海，5月4日返回
  [正在为您搜索方案...]
  方案 1：SQ830 09:30 到达 → 入住瑞吉酒店 12:00...
  方案 2：MU512 13:00 到达 → 入住四季酒店 16:00...

> 我选方案1，确认预订
```

---

A2A POC 完整方案文档 · v1.1  
LangChain · LangGraph · A2A Protocol · PostgreSQL