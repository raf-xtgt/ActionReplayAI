import dspy
from pydantic import BaseModel, Field
from typing import List, Optional
from model.context_model import ( ConversationAnalysis, ClientAgentContextModel, CoachAgentProblemAnalysis, CoachAgentSolutionAnalysis )
from .prompt import (get_coach_agent_classification_prompt, get_coach_agent_behavioral_cue_prompt, get_coach_agent_risk_prompt)
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from util.inference_service import ( get_llm_output )
from util.db_service import (get_solutions_to_objections)
import json

class AlternatorAgent:
    def __init__(self):
        self.alternator = ""