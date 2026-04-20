import asyncio
from pathlib import Path
from sqlalchemy import create_engine
from db.models import Base
from launcher import start_agents
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import uvicorn
import os
from dotenv import load_dotenv
from agents.orchestrator import OrchestratorState

load_dotenv()

app = FastAPI(title="A2A POC API", version="1.0.0")

# Serve frontend from the same process
FRONTEND_DIR = Path(__file__).resolve().parent / 'frontend'
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/poc.html")

@app.get("/poc.html")
async def get_poc():
    return FileResponse(FRONTEND_DIR / 'poc.html')

@app.get("/test.html")
async def get_test():
    return FileResponse(FRONTEND_DIR / 'test.html')

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_input: str
    chat_history: List[dict] = []  # [{"role": "user"|"assistant", "content": "..."}]

class ChatResponse(BaseModel):
    combined_options: list
    llm_summary: str = ""
    intent: str = ""

orchestrator_graph = None

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    global orchestrator_graph
    if not orchestrator_graph:
        raise HTTPException(status_code=500, detail="Orchestrator not initialized")

    try:
        initial_state: OrchestratorState = {
            "user_input": request.user_input,
            "chat_history": request.chat_history,
            "parsed_params": {},
            "intent": "",
            "flight_options": {},
            "hotel_options": [],
            "combined_options": [],
            "selected_option": {},
            "llm_summary": "",
        }

        result = await orchestrator_graph.ainvoke(initial_state)
        return ChatResponse(
            combined_options=result.get('combined_options', []),
            llm_summary=result.get('llm_summary', ''),
            intent=result.get('intent', ''),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def main():
    global orchestrator_graph
    # Initialize DB
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://a2a_user:a2a_password@localhost:5432/a2a_poc')
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("✓ DB initialized")

    # Start agents
    orchestrator_graph = await start_agents()

    # Start API server
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    print("✓ API server starting on http://localhost:8000")
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())