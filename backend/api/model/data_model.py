from pydantic import BaseModel
from typing import List


class ClientProfileResponse(BaseModel):
    id: str
    name: str
    description: str

class ConversationRound(BaseModel):
    client_message: str
    user_response: str

class CoachAnalysis(BaseModel):
    is_substantive: bool
    behavioral_cues: List[str] = []
    risks: List[str] = []
    techniques: List[str] = []
    alternative_paths: List[str] = []
    micro_feedback: str = ""
