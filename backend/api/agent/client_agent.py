from typing import Optional, Dict, List
from pydantic import BaseModel, Field
import os
from util.db_service import (get_client_profile, get_client_objections)
from model.context_model import ( ClientAgentContextModel )
from dotenv import load_dotenv
import requests
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from .prompt import (get_client_agent_prompt)

load_dotenv()


def get_llm_output(client_agent_prompt: str) -> str:
    response = requests.post(
        "https://api.moonshot.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('KIMI_API_KEY')}"
        },
        json={
            "model": "moonshot-v1-32k",
            "messages": [
                {"role": "system", "content": client_agent_prompt}
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
        client_agent_prompt = get_client_agent_prompt(client_agent_context)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(get_llm_output, client_agent_prompt)
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