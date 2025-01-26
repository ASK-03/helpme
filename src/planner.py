from llm import LLMEngine
from config import DEFAULT_MODELS, ExecutionState


class StepPlanner:
    def __init__(self, provider: str):
        self.llm = LLMEngine()
        self.provider = provider
        self.model = DEFAULT_MODELS[provider]

    def generate_next_step(self, instruction: str, state: ExecutionState) -> dict:
        previous_steps = self._format_all_previous_steps(state)

        prompt = f"""You are an advanced shell command planner. Analyze the execution history and devise the next optimal step.

# TASK
{instruction}

# EXECUTION CONTEXT
## Current Environment
- Completed Steps: {len(state['previous_steps'])}
- Last Status: {state['current_status']}

## Command History
{previous_steps or 'No steps executed yet'}

## Validation Feedback
{self._format_feedback(state['feedback_history']) or 'No feedback'}

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

# OUTPUT FORMAT
{{
    "step": "Clear purpose linking to task and history",
    "command": "Precise shell command using existing context",
    "reason": "Technical justification referencing specific previous steps/outputs. Example: 'Using Step 1's file contents to...'",
    "completed": true/false  // Only true if ALL task requirements are met
}}

Example for file reading:
Task: "Read config.txt and give its summary"
Step 1: {{
    "command": "cat config.txt",
    "reason": "Read config file contents as requested",
}}
Step 2: {{
    "command": "echo 'SUMMARY OF THE FILE *config.txt*'",
    "reason": "Got the content of *config.txt* from previous step's output."
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
                f"  Command: {step.get('command', 'N/A')}\n"
                f"  Output: {step.get('execution_result', {}).get('output', 'No output')}\n"
                f"  Status: {'Success' if step.get('execution_result', {}).get('success') else 'Failed'}\n"
                f"  Reason: {step.get('reason', 'No reason provided')}"
            )
        return "\n\n".join(step_list)

    def _format_feedback(self, feedback_history: list) -> str:
        """Format feedback history for prompt"""
        if not feedback_history:
            return "No feedback yet"
        return "\n- ".join(
            [f"[Step {i+1}] {fb}" for i, fb in enumerate(feedback_history)]
        )
