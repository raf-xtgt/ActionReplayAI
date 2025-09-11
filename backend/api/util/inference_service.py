import requests
import os
from dotenv import load_dotenv
load_dotenv()


def get_llm_output(prompt: str) -> str:
    response = requests.post(
        "https://api.moonshot.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.getenv('KIMI_API_KEY')}"
        },
        json={
            "model": "moonshot-v1-32k",
            "messages": [
                {"role": "system", "content": prompt}
            ]
        }
    )
    response.raise_for_status()  # Raise an exception for bad status codes
    return response.json()["choices"][0]["message"]["content"]
