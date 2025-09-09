from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import dspy
import json
import re
import os
from util.db_service import (get_client_profile, get_client_objections)
import os
from dotenv import load_dotenv
import signal
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

load_dotenv()

@contextmanager
def timeout(duration):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {duration} seconds")
    
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(duration)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)  # restore old handler


# Use Kimi (Moonshot AI)
client_lm = dspy.LM(
    "moonshot-v1-32k",  # or "moonshot-v1" depending on your subscription
    api_base="https://api.moonshot.cn/v1",
    api_key=os.getenv("KIMI_API_KEY"),
    timeout=45,  
    max_retries=2
)
dspy.configure(lm=client_lm)

class ContextModel(BaseModel):
    profile_desc: str
    current_objection: str
    all_objections: List[str]  # list of all client objections
    related_objections: List[str]  # objections not raised but related
    conversation_history: Optional[List[Dict]] = None

class ClientAgentContext(dspy.Signature):
    """
    You are a demanding customer dealing with a salesman. Your role is to simulate a real client 
    based on the provided profile and objections. You should be skeptical, ask challenging questions, 
    and maintain the concerns typical for your profile. Be authentic and don't make it easy for the salesman.
    Instructions:
    1. Start by raising the current objection naturally in conversation
    2. Respond to the salesman's answers with follow-up questions or skepticism
    3. Maintain your persona as described in the client profile
    4. If the salesman addresses your objection well, consider raising another objection from your list
    5. Be authentic and challenging - don't concede easily
    6. Keep responses concise (1-2 sentences typically)
    """
    context: ContextModel = dspy.InputField(desc="Context about the client profile and objections")
    output: str = dspy.OutputField(desc="Your response as the client")

class ClientAgent(dspy.Module):
    def __init__(self):
        self.agent_output = dspy.Predict(ClientAgentContext)
        self.conversation_history = []

    def forward(self, client_profile_id, user_response=None):
        
        # If this is a subsequent turn, add user response to history
        if user_response:
            self.conversation_history.append({"role": "salesman", "content": user_response})
            
        context = self.construct_profile_desc(client_profile_id)
        print("Context", json.dumps(context, indent=2, default=str) )
            
        print("prediction start")
        try:
            with timeout(45):  # This should interrupt if stuck
                output = self.agent_output(context=context)
                print("Output", output)
        except TimeoutError as e:
            print(f"Prediction timed out: {e}")
            return "I'm still thinking about your offer. This is taking longer than expected."  # fallback
        except Exception as e:
            print(f"Error during prediction: {e}")
            return "Something went wrong in our discussion."
        # Add client response to history
        self.conversation_history.append({"role": "client", "content": output.output})
            
        return output.output
   

    def construct_profile_desc(self, client_profile_id):
        client_profile = get_client_profile(client_profile_id)
        print("Client Profile", json.dumps(client_profile, indent=2, default=str) )
        objections = get_client_objections(client_profile_id)
        print("Client Objections", json.dumps(objections, indent=2, default=str) )

        
        # Get the next objection to raise (cycle through them)
        current_objection_idx = len(self.conversation_history) // 2  # Each round has client + user messages
        if current_objection_idx >= len(objections["client_objections"]):
            current_objection_idx = len(objections["client_objections"]) - 1  # Stay on last objection
        
        current_objection = objections["client_objections"][current_objection_idx] if objections["client_objections"] else "No specific objection"
        
        context_model = ContextModel(
            profile_desc=client_profile["description"], 
            current_objection=current_objection,
            all_objections=objections["client_objections"],
            related_objections=objections["related_objections"],
            conversation_history=self.conversation_history.copy()
        )
        return context_model