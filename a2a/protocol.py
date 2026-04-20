from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

class MessagePart(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = None

class Message(BaseModel):
    role: str
    parts: List[MessagePart]

class Task(BaseModel):
    id: str = str(uuid.uuid4())
    sender: str
    receiver: str
    status: str = 'pending'
    message: Message
    created_at: datetime = datetime.utcnow()

class AgentCard(BaseModel):
    id: str
    name: str
    capabilities: List[str]
    endpoint: str