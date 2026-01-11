from abc import ABC, abstractmethod
from typing import Dict, Any, Protocol, List
from src.core.context import ExecutionState

class Planner(ABC):
    @abstractmethod
    def generate_next_step(self, instruction: str, state: ExecutionState) -> Dict[str, Any]:
        """Generate the next execution step."""
        pass

class Validator(ABC):
    @abstractmethod
    def validate_step(self, instruction: str, proposed_step: Dict[str, Any], state: ExecutionState) -> Dict[str, Any]:
        """Validate a proposed step."""
        pass

class Executor(ABC):
    @abstractmethod
    def execute(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        """Execute a shell command."""
        pass
    
    @abstractmethod
    def close(self):
        """Clean up resources."""
        pass

class UIProvider(Protocol):
    def print_plan(self, step: Dict[str, Any]): ...
    def print_validation(self, validation: Dict[str, Any]): ...
    def print_execution_result(self, step: Dict[str, Any], result: Dict[str, Any]): ...
    def print_error(self, message: str): ...
    def print_success(self, message: str): ...
    def print_status(self, message: str): ...

class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, model: str, format: str = "text", **kwargs) -> Dict[str, Any]:
        """Generate content from LLM."""
        pass
