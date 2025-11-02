import os
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Literal
import google.generativeai as genai
import openai
import requests
import ollama
from google.generativeai import GenerationConfig


class LLMConfigurationError(Exception):
    """Exception raised for configuration errors in LLM providers"""

    pass


class LLMResponseError(Exception):
    """Exception raised for API response errors"""

    pass


class BaseProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        model: str,
        format: Literal["text", "json"] = "text",
        **kwargs,
    ) -> Dict[str, Any]:
        pass


class GeminiProvider(BaseProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise LLMConfigurationError("GEMINI_API_KEY not found in environment")
        genai.configure(api_key=api_key)

    def generate(
        self, prompt: str, model: str, format: str = "text", **kwargs
    ) -> Dict[str, Any]:
        try:
            config = GenerationConfig(
                temperature=0,
                top_p=1.0,
                top_k=50,
                max_output_tokens=4096,
                response_mime_type=(
                    "application/json" if format == "json" else "text/plain"
                ),
            )
            model = genai.GenerativeModel(model, generation_config=config)
            response = model.generate_content(prompt)
            return {"content": response.text, "status": "success", "format": format}
        except Exception as e:
            raise LLMResponseError(f"Gemini API error: {str(e)}")


class OpenAIProvider(BaseProvider):
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY not found in environment")
        self.client = openai.OpenAI(api_key=api_key)

    def generate(
        self, prompt: str, model: str, format: str = "text", **kwargs
    ) -> Dict[str, Any]:
        try:
            response_format = (
                {"type": "json_object"} if format == "json" else {"type": "text"}
            )
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=response_format,
                **kwargs,
            )
            return {
                "content": response.choices[0].message.content,
                "status": "success",
                "format": format,
            }
        except Exception as e:
            raise LLMResponseError(f"OpenAI API error: {str(e)}")


class DeepSeekProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise LLMConfigurationError("DEEPSEEK_API_KEY not found in environment")
        self.base_url = "https://api.deepseek.com/v1/chat/completions"

    def generate(
        self, prompt: str, model: str, format: str = "text", **kwargs
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            **kwargs,
        }
        if format == "json":
            data["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(self.base_url, json=data, headers=headers)
            response.raise_for_status()
            return {
                "content": response.json()["choices"][0]["message"]["content"],
                "status": "success",
                "format": format,
            }
        except Exception as e:
            raise LLMResponseError(f"DeepSeek API error: {str(e)}")


class OllamaProvider(BaseProvider):
    def generate(
        self, prompt: str, model: str, format: str = "text", **kwargs
    ) -> Dict[str, Any]:
        try:
            response = ollama.generate(
                model=model,
                prompt=prompt,
                options=ollama.Options(temperature=0)
            )

            content = response["response"].strip()
            if model == 'deepseek-r1':
                content = self._format_deepseek_output(content)

            print("OLLAMA RESPONSE FROM DEEPSEEK-R1:1.5B -> ", content)
            if format == "json":
                content = json.loads(content)
            return {"content": content, "status": "success", "format": format}
        except Exception as e:
            raise LLMResponseError(f"Ollama error: {str(e)}")

    def _format_deepseek_output(self, content: str) -> str:
        # Remove <think> blocks including their content
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        
        # Find the JSON code block using non-greedy match
        json_match = re.search(
            r'```json\s*(.*?)\s*```', 
            content, 
            flags=re.DOTALL
        )
        
        if json_match:
            return json_match.group(1).strip()
        return ''

class LLMEngine:
    _providers = {
        "ollama": OllamaProvider,
        "gemini": GeminiProvider,
        "openai": OpenAIProvider,
        "deepseek": DeepSeekProvider,
    }

    def __init__(self):
        self.provider_map = {}

    def get_provider(self, provider_name: str) -> BaseProvider:
        provider_name = provider_name.lower()
        if provider_name not in self._providers:
            raise ValueError(f"Provider {provider_name} not registered")
        if provider_name not in self.provider_map:
            self.provider_map[provider_name] = self._providers[provider_name]()
        return self.provider_map[provider_name]

    def generate(
        self,
        prompt: str,
        provider: str,
        model: str,
        format: Literal["text", "json"] = "text",
        **kwargs,
    ) -> Dict[str, Any]:
        provider_instance = self.get_provider(provider)
        response = provider_instance.generate(prompt, model, format, **kwargs)
        if format == "json" and isinstance(response["content"], str):
            try:
                response["content"] = json.loads(response["content"])
            except json.JSONDecodeError:
                raise LLMResponseError("Failed to parse JSON response")
        return response
