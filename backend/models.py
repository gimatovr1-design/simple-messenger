from pydantic import BaseModel

class ChatMessage(BaseModel):
    user: str
    text: str
    timestamp: str
    system: bool = False
