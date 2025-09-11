import dspy
from pydantic import BaseModel, Field
from typing import List, Optional
from model.context_model import ( ConversationAnalysis, ClientAgentContextModel )
from .prompt import (get_coach_agent_classification_prompt)
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from util.inference_service import ( get_llm_output )

class CoachAgentSignature(dspy.Signature):
    """Analyzes the conversation and provides feedback to the user."""

    conversation_history: str = dspy.InputField(desc="The history of the conversation so far.")
    user_response: str = dspy.InputField(desc="The user's latest response.")
    session_cache: str = dspy.InputField(desc="The session cache, containing relevant information.")
    analysis: ConversationAnalysis = dspy.OutputField(desc="The analysis of the conversation.")

class UserResponseClassificationSignature(dspy.Signature):
    """Classify the user's response as 'substantive' or 'minor'."""
    conversation_history: str = dspy.InputField(desc="The history of the conversation so far.")
    user_response: str = dspy.InputField(desc="The user's latest response.")
    classification: str = dspy.OutputField(desc="Either 'substantive' or 'minor'.")

class SubstantiveAnalysisSignature(dspy.Signature):
    """Analyzes a substantive user response and provides a detailed report."""
    conversation_history: str = dspy.InputField(desc="The history of the conversation so far.")
    session_cache: str = dspy.InputField(desc="The session cache, containing relevant information.")
    behavioral_cues: List[str] = dspy.OutputField(desc="List of identified behavioral cues, from strongest to weakest.")
    risks: List[str] = dspy.OutputField(desc="Unaddressed objections and consequential objections.")
    techniques: List[str] = dspy.OutputField(desc="Techniques available from the session cache to address the risks.")

class CoachAgent:
    def __init__(self):
        self.classification = ""

    def forward(self, client_agent_context: ClientAgentContextModel):
        classification_prompt = get_coach_agent_classification_prompt(client_agent_context)
        classification_output = ""
        print("coach classification start")
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_output, classification_prompt)
            try:
                classification_output = future.result(timeout=45)
                print("coach agent classification response", classification_output)
            except FutureTimeoutError:
                return "Prediction timed out after 45 seconds"
            except Exception as e:
                return f"Error during prediction: {e}"

        # Add client response to history
        return classification_output