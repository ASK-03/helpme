from typing import Dict, Any
from src.core.interfaces import Planner
from src.core.context import ExecutionState
from src.providers.llm import LLMEngine
from src.config.constants import DEFAULT_MODELS
from src.common.prompts import PLANNER_PROMPT
import os

class StepPlanner(Planner):
    def __init__(self, provider: str):
        self.llm = LLMEngine()
        self.provider = provider
        self.model = DEFAULT_MODELS[provider]

    def generate_next_step(self, instruction: str, state: ExecutionState) -> Dict[str, Any]:
        previous_steps_str = self._format_all_previous_steps(state)
        
        prompt = PLANNER_PROMPT.format(
            instruction=instruction,
            os_name=os.name,
            current_directory=state['current_directory'],
            previous_steps=previous_steps_str
        )

        response = self.llm.generate(
            prompt=prompt, provider=self.provider, model=self.model, format="json"
        )
        
        content = response["content"]
        # Ensure 'completed' key exists
        if hasattr(content, 'get'):
             content["completed"] = content.get("completed", False)
             
        return content

    def _format_all_previous_steps(self, state: ExecutionState) -> str:
        if not state["previous_steps"]:
            return "  No steps executed yet"

        step_list = []
        for i, step in enumerate(state["previous_steps"], 1):
            step_list.append(
                f"Step {i}:\n"
                f"\tstep: {step.get('step', 'N/A')}\n"
                f"\tcommand: {step.get('command', 'N/A')}\n"
                f"\toutput: {step.get('output', 'No Output')}\n"
                f"\tstatus: {'Success' if step.get('completed', False) else 'Failed'}\n"
                f"\treason: {step.get('reason', 'No reason provided')}\n"
                f"\tfeedback: {step.get('feedback', 'No feedback provided')}\n"
            )
        return "\n\n".join(step_list)
