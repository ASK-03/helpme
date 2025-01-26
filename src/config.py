import os
from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()

DEFAULT_MODELS = {
    "ollama": "deepseek-r1",
    "gemini": "gemini-1.5-flash",
    "openai": "gpt-4",
    "deepseek": "deepseek-chat",
}


class ExecutionState(TypedDict):
    # TODO: Add current directory, reason: Model is loosing track of current directory and making hallucinated decision 
    completed: bool
    previous_steps: list[dict]
    current_status: str
    feedback_history: list[str]
