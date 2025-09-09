from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import dspy
import json
import re
import os
from util.db_service import ( get_client_profile, get_client_objections )


client_lm = dspy.LM("ollama_chat/llama3.1:latest", api_base="http://localhost:11434", api_key="")
dspy.configure(lm=client_lm)

class ContextModel(BaseModel):
    profile_desc: str
    current_objection: str
    all_objections: List[str] # list of all client objections
    related_objections: List[str] # objections not raised but related

class ClientAgentContext(dspy.Signature):
    """
    You are a demanding customer dealing with a salesman 
    """
    context: ClientAgentContext = dspy.InputField()
    output: str = dspy.OutputField()


class ClientAgent(dspy.Module):
    def __init__(self):
        self.agent_output = dspy.Predict(ClientAgentContext)

    def forward(self, client_profile_id):
        context = self.construct_profile_desc(client_profile_id)
        output = self.agent_output(context)
        return output

    def construct_profile_desc(self, client_profile_id):
        client_profile = get_client_profile(client_profile_id)
        objections = get_client_objections(client_profile_id)
        
        context_model = ContextModel(
            client_profile["description"], 
            objections["client_objections"][0],
            objections["client_objections"][1:],
            objections["related_objections"]
        )
        return context_model
