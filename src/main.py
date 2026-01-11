import os
import time
from typing import Optional

from src.core.context import ExecutionState
from src.services.planner import StepPlanner
from src.services.validator import StepValidator
from src.services.executor import PersistentShell
from src.ui.console import ConsoleUI
from src.core.exceptions import HelpMeError

class App:
    def __init__(self, provider: str = "ollama"):
        self.provider = provider
        self.ui = ConsoleUI()
        self.planner = StepPlanner(provider)
        self.validator = StepValidator(provider)
        self.shell = PersistentShell()

    def run(self, instruction: str):
        # Initialize state
        state: ExecutionState = {
            "completed": False,
            "previous_steps": [],
            "current_directory": os.getcwd(),
        }

        try:
            with self.shell:
                while not state["completed"]:
                    # Planning phase
                    self.ui.print_planning()
                    step = self.planner.generate_next_step(instruction, state)

                    # Validation phase
                    self.ui.print_validating()
                    validation = self.validator.validate_step(instruction, step, state)

                    if validation["approved"]:
                        command = validation.get("modification") or step.get("command")

                        if not command:
                            self.ui.print_error("No valid command to execute!")
                            break

                        result = self.shell.execute(command, timeout=step.get("timeout", 60))

                        # Use 'step' key safely, fallback to index if missing
                        step_num = step.get('step', len(state['previous_steps']) + 1)
                        self.ui.print_step_summary(step, validation, result, step_num) # type: ignore

                        # Update state
                        state["previous_steps"].append(
                            {
                                "step": step.get("step", ""),
                                "timeout": step.get("timeout", 60),
                                "command": command,
                                "reason": step.get("reason", ""),
                                "completed": result["success"],
                                "output": result["output"],
                                "feedback": (
                                    f"{validation.get('feedback', 'No feedback')}"
                                    + (
                                        f" | {validation['modification']}"
                                        if validation.get("modification")
                                        else ""
                                    )
                                ),
                            }
                        )

                        state["completed"] = step.get("completed", False) and result.get("success", False)
                        # Check exit code or shell state if needed
                        
                    else:
                        self.ui.print_step_rejected(step, validation)
                        state["previous_steps"].append({
                            "step": step.get("step", ""),
                            "timeout": 0,
                            "command": "",  # Empty since step was rejected
                            "completed": False,
                            "feedback": validation["feedback"],
                            "reason": step.get("reason", ""),
                            "output": ""  # Empty since step was not executed
                        })
                    
                    time.sleep(0.4)

            self.ui.print_success("Task Completed Successfully!")

        except HelpMeError as e:
            self.ui.print_error(str(e))
        except Exception as e:
            self.ui.print_error(f"Unexpected error: {str(e)}")

def main(instruction: str, provider: str):
    app = App(provider)
    app.run(instruction)
