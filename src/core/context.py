from typing import TypedDict, List, Optional

class Step(TypedDict):
    step: str
    timeout: int
    command: str
    completed: bool
    feedback: str
    reason: str
    output: Optional[str]

class ExecutionState(TypedDict):
    completed: bool
    previous_steps: List[Step]
    current_directory: str
