import dspy
from pydantic import BaseModel, Field
from typing import Optional, Dict, List


class ClientAgentContextModel(BaseModel):
    profile_desc: str
    current_objection: str
    all_objections: List[str]  # list of all client objections
    related_objections: List[str]  # objections not raised but related
    conversation_history: Optional[List[Dict]] = None


class SessionModel(BaseModel):
    session_id: str
    client_agent_context: ClientAgentContextModel
    round_count:int

class ConversationAnalysis(BaseModel):
    classification: str = Field(description="Classification of the user's response.")
    micro_feedback: Optional[str] = Field(description="Micro-feedback for minor responses.")
    behavioral_cues: Optional[List[str]] = Field(description="List of identified behavioral cues, from strongest to weakest.")
    risks: Optional[List[str]] = Field(description="Unaddressed objections and consequential objections.")
    techniques: Optional[List[str]] = Field(description="Techniques available from the session cache to address the risks.")
    alternative_paths: Optional[List[str]] = Field(description="Alternative conversation paths to address client objections.")
