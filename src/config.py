from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()

DEFAULT_MODELS = {
    "ollama": "deepseek-r1",
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4",
    "deepseek": "deepseek-chat",
}

class Step(TypedDict):
    step: str
    timeout: int
    command: str
    completed: bool
    feedback: str
    reason: str
    output: str

class ExecutionState(TypedDict):
    completed: bool
    previous_steps: list[Step]
    current_directory: str
