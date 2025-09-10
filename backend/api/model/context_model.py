import dspy
from pydantic import BaseModel
from typing import Optional, Dict, List


class ClientAgentContextModel(BaseModel):
    profile_desc: str
    current_objection: str
    all_objections: List[str]  # list of all client objections
    related_objections: List[str]  # objections not raised but related
    conversation_history: Optional[List[Dict]] = None
    latest_client_response: Optional[str]



class SessionCacheModel(BaseModel):
    session_id: str
    client_agent_context: ClientAgentContextModel
    round_count:int
