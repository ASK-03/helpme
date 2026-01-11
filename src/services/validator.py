from typing import Dict, Any
from src.core.interfaces import Validator
from src.core.context import ExecutionState
from src.providers.llm import LLMEngine
from src.config.constants import DEFAULT_MODELS
from src.common.prompts import VALIDATOR_PROMPT

class StepValidator(Validator):
    def __init__(self, provider: str):
        self.llm = LLMEngine()
        self.provider = provider
        self.model = DEFAULT_MODELS[provider]

    def validate_step(
        self, instruction: str, proposed_step: Dict[str, Any], state: ExecutionState
    ) -> Dict[str, Any]:
        previous_commands = [s['command'] for s in state['previous_steps']]
        
        prompt = VALIDATOR_PROMPT.format(
            instruction=instruction,
            step_description=proposed_step.get('step', ''),
            command=proposed_step.get('command', ''),
            reason=proposed_step.get('reason', ''),
            current_directory=state['current_directory'],
            previous_commands=previous_commands
        )

        response = self.llm.generate(
            prompt=prompt, provider=self.provider, model=self.model, format="json"
        )

        return response["content"]
