from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import uuid
from datetime import datetime

#define agent communication protocol

class MessagePart(BaseModel):  # a single part of a message
    text: str
    metadata: Optional[Dict[str, Any]] = None

class Message(BaseModel):    # whole message
    role: str
    parts: List[MessagePart]

class Task(BaseModel):   # waht to do
    id: str = str(uuid.uuid4())
    sender: str
    receiver: str
    status: str = 'pending'
    message: Message
    created_at: datetime = datetime.utcnow()

class AgentCard(BaseModel):     # to describe agents in the system
    id: str
    name: str
    capabilities: List[str]
    endpoint: str