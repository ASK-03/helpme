from llm import LLMEngine
from config import DEFAULT_MODELS, ExecutionState


class StepValidator:
    def __init__(self, provider: str):
        self.llm = LLMEngine()
        self.provider = provider
        self.model = DEFAULT_MODELS[provider]

    def validate_step(
        self, instruction: str, proposed_step: dict, state: ExecutionState
    ) -> dict:
        prompt = f"""
You are a shell command validator. Analyze the proposed step in context.

# Security Rules
    1. Donot approve reboot, restart commands
    2. If command seems harmful, suggest safer alternative
    3. Avoid commands that can delete or corrupt data
    4. Ensure commands that download or install software are safe
    5. Commands that download software must use official sources
    6. If download command is present, ensure if the software is already installed

Overall Instruction: {instruction}
Proposed Step:
- Description: {proposed_step['step']}
- Command: {proposed_step['command']}
- Reason: {proposed_step['reason']}

Execution Context:
- Current Directory: {state['current_directory']}
- Previous Commands: {[s['command'] for s in state['previous_steps']]}

Output JSON with:
- "approved": Boolean
- "feedback": Technical assessment
- "modification": Suggested command modification
"""

        response = self.llm.generate(
            prompt=prompt, provider=self.provider, model=self.model, format="json"
        )

        return response["content"]
