import os
from dotenv import load_dotenv

load_dotenv()

def get_api_key(provider_name: str) -> str:
    key_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
    }
    env_var = key_map.get(provider_name.lower())
    if env_var:
        return os.getenv(env_var, "")
    return ""
