import dspy
from pydantic import BaseModel, Field
from typing import List, Optional
from model.context_model import ( ConversationAnalysis )

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

class CoachAgent(dspy.Module):
    def __init__(self):
        super().__init__()
        self.deepseek = dspy.OllamaLocal(model="deepseek-r1:latest")
        self.classify = dspy.ChainOfThought(UserResponseClassificationSignature)
        self.substantive_analysis = dspy.ChainOfThought(SubstantiveAnalysisSignature)

    def forward(self, conversation_history, user_response, session_cache):
        dspy.settings.configure(lm=self.deepseek)

        # Classify the user's response
        classification_result = self.classify(conversation_history=conversation_history, user_response=user_response)
        classification = classification_result.classification

        if classification.lower() == 'minor':
            # Provide micro-feedback
            analysis = ConversationAnalysis(
                classification='minor',
                micro_feedback='This is a good start. Try to elaborate more on your solution.',
                behavioral_cues=None,
                risks=None,
                techniques=None,
                alternative_paths=None
            )
        else:
            # Perform substantive analysis
            analysis_result = self.substantive_analysis(conversation_history=conversation_history, session_cache=session_cache)
            
            # Mock interaction with SessionManagerAgent and AlternatorAgent
            alternative_paths = [
                "Path 1: Focus on the cost savings of your solution.",
                "Path 2: Highlight the security features of your product.",
                "Path 3: Share a case study of a similar client who benefited from your solution."
            ]

            analysis = ConversationAnalysis(
                classification='substantive',
                behavioral_cues=analysis_result.behavioral_cues,
                risks=analysis_result.risks,
                techniques=analysis_result.techniques,
                alternative_paths=alternative_paths,
                micro_feedback=None
            )
        
        return dspy.Prediction(analysis=analysis)