# 系统架构

## 根目录
- a2a-poc/

## 前端层 ✅
- frontend/
  - poc.html // 🎯 **主界面** - 仪表盘 UI · 实时对话 · A2A流可视化 · 日志面板 · 完全集成后端API
  - test.html // 📊 测试页面 - 验证API数据完整性

## 启动 + 路由层
- main.py // 📡 **改进**: FastAPI服务器 (CORS支持) + 异步SQLAlchemy + DB初始化
- cli.py // readline 自然语言交互循环 (可选)
- launcher.py // asyncio 统一启动三个智能体服务

## A2A 协议层
- a2a/
  - protocol.py 
  - router.py // 进程内消息路由，替代 HTTP，保留协议语义

## 智能体层
- agents/
  - orchestrator.py // LangGraph StateGraph · 意图解析 · 任务编排
  - flight_agent.py // 航班搜索智能体
  - hotel_agent.py // 酒店匹配智能体

## 工具层
- tools/
  - flight_search.py // 返回格式: {flight_number, airline, departure_time, arrival_time, price, duration}
  - hotel_search.py // 返回格式: {name, area, stars, checkin_time, checkout_time, price}

## 数据库层
- db/
  - models.py 
  - session.py 
  - state_store.py 

## Mock 数据 ✅ **更新**
- mock_data/
  - flights.json // ✨ 新增: airline 字段、duration 字段
  - hotels.json // ✨ 新增: area 字段、stars 字段 | 改: price_per_night → price

## 配置 + 基础设施
- .env // 环境变量
- docker-compose.yml // PostgreSQL容器
- requirements.txt // 依赖管理
- README.md // 启动说明 · 架构概览
- FRONTEND_INTEGRATION_REPORT.md // ✅ 前端集成完成报告

---

## 🚀 快速启动

### 启动所有服务
```bash
# 终端1: 后端API (端口8000, CORS已启用)
cd /Users/kyle/Documents/Doxa/A2A_POC_Rui
source venv/bin/activate
python main.py

# 终端2: 前端服务器 (端口3000)
cd /Users/kyle/Documents/Doxa/A2A_POC_Rui/frontend
python3 -m http.server 3000
```

### 访问应用
- 🎯 **主界面**: http://localhost:3000/poc.html
- 📊 **测试**: http://localhost:3000/test.html
- 📡 **API**: http://localhost:8000/chat (POST)

### 验证集成
```bash
python3 test_frontend.py
```

---

## 已解决的问题 ✅

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 前端无法连接后端 | 缺少CORS支持 | FastAPI添加CORSMiddleware |
| 数据字段缺失 | mock_data不完整 | 更新flights.json和hotels.json |
| 前端显示错误 | 数据映射不匹配 | 更新前端数据字段引用 |
| API不可用 | 端口冲突 | 自动清理端口并重启服务 |
