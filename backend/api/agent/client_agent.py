from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import os
from util.db_service import (get_client_profile, get_client_objections)
from model.context_model import ( ClientAgentContextModel )
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

load_dotenv()
client_agent_prompt = """You are a demanding customer dealing with a salesman. Your role is to simulate a real client based on the provided profile and objections. 
You should be skeptical, ask challenging questions, and maintain the concerns typical for your profile. Be authentic and don't make it easy for the salesman.

Instructions:
    1. Start by raising the current objection naturally in conversation
    2. Respond to the salesman's answers with follow-up questions or skepticism
    3. Maintain your persona as described in the client profile
    4. If the salesman addresses your objection well, consider raising another objection from your list
    5. Be authentic and challenging - don't concede easily
    6. Keep responses concise (1-2 sentences typically)
"""


def get_llm_output(context_prompt: str) -> str:
    response = requests.post(
        "https://api.moonshot.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('KIMI_API_KEY')}"
        },
        json={
            "model": "moonshot-v1-32k",
            "messages": [
                {"role": "system", "content": client_agent_prompt + "\nContext:\n" + context_prompt}
            ]
        }
    )
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()["choices"][0]["message"]["content"]

class ClientAgent:
    def __init__(self):
        self.conversation_history = []

    def forward(self, client_agent_context: ClientAgentContextModel):
        output = ""
        print("prediction start")
        context_prompt = f"Client Profile: {client_agent_context.profile_desc}\n\nObjections: {client_agent_context.current_objection}\n\nConversation History: {client_agent_context.conversation_history}"
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_output, context_prompt)
            try:
                output = future.result(timeout=45)
                print("Client agent response", output)
            except FutureTimeoutError:
                print("Prediction timed out after 45 seconds")
                # Optionally, you can add a fallback response here
                client_agent_context.conversation_history.append({"role": "client_agent", "content": "I'm still thinking about your offer. This is taking longer than expected."})
                return client_agent_context
            except Exception as e:
                print(f"Error during prediction: {e}")
                # Optionally, you can add a fallback response here
                client_agent_context.conversation_history.append({"role": "client_agent", "content": "Something went wrong in our discussion."})
                return client_agent_context

        # Add client response to history
        client_agent_context.conversation_history.append({"role": "client_agent", "content": output})
        return client_agent_context