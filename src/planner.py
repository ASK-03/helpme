import os
from llm import LLMEngine
from config import DEFAULT_MODELS, ExecutionState


class StepPlanner:
    def __init__(self, provider: str):
        self.llm = LLMEngine()
        self.provider = provider
        self.model = DEFAULT_MODELS[provider]

    def generate_next_step(self, instruction: str, state: ExecutionState) -> dict:
        previous_steps = self._format_all_previous_steps(state)

        prompt = f"""
You are an advanced shell command planner.
You will be running in a loop with context (previous command, its output) of the previous steps,
you should break the TASK into small steps and focus on completing the task one step at a time.
Break the task down logically and ensure each step is purposeful and builds towards the final goal.
The goal is to complete the TASK. Keep the quality of each step high.

Analyze the task, execution history and devise the next optimal step.

# TASK
{instruction}

# EXECUTION CONTEXT
## Current Environment
- OS: { os.name }
- Current Directory: {state['current_directory']}

## Command History
{previous_steps or 'No steps executed yet'}

# PLANNING REQUIREMENTS
1. Check command history to avoid redundancy
2. Use successful outputs from previous steps
3. Never repeat directory navigation without new purpose
4. Progress toward completing ALL task requirements
5. Explain how this step builds on previous results
6. For file reading tasks:
   - Use `cat` to get file contents when needed
   - Store output using command substitution if required
   - Reference file contents from previous steps' outputs
7. Provide only one step at a time.
8. Donot give command that produces a very long output.
9. If the task is to explain something, use echo command to output the explanation.
10. Before suggesting download/install commands, check if software is already installed.

Remember to strictly adhere to the JSON format below.

# OUTPUT FORMAT
{{
    "step": "Clear purpose linking to task and history",
    "timeout": 60,  // estimated time in seconds to complete this step
    "command": "Precise shell command using existing context",
    "reason": "Technical justification referencing specific previous steps/outputs and how will this commands output will be used in subsequent steps. Example: 'Using Step 1's file contents to...'",
    "completed": true/false  // Only true if ALL task requirements are met
    "feedback": []  // feedback will be provided by validator in next phase
    "output": ""  // output will be filled after execution
}}

Generate the next step JSON:"""

        response = self.llm.generate(
            prompt=prompt, provider=self.provider, model=self.model, format="json"
        )

        return {
            **response["content"],
            "completed": response["content"].get("completed", False),
        }

    def _format_all_previous_steps(self, state: ExecutionState) -> str:
        """Format complete step history for inclusion in prompt"""
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

    def _format_feedback(self, feedback_history: list) -> str:
        """Format feedback history for prompt"""
        if not feedback_history:
            return "No feedback yet"
        return "\n- ".join(
            [f"[Step {i+1}] {fb}" for i, fb in enumerate(feedback_history)]
        )
