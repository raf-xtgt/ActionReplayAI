from pydantic import BaseModel, Field
from datetime import datetime

class Message(BaseModel):
    text: str
    sender_type: str
    msg_time: datetime = Field(default_factory=datetime.now)
