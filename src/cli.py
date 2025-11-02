import os
import typer
import time
from rich.console import Console
from planner import StepPlanner
from validator import StepValidator
from executor import PersistentShell
from config import ExecutionState, DEFAULT_MODELS

console = Console()
app = typer.Typer()


@app.command()
def run(
    instruction: str = typer.Argument(..., help="Task to perform"),
    provider: str = typer.Option(
        "ollama",
        "--provider",
        "-p",
        help="LLM provider (ollama, gemini, openai, deepseek)",
    ),
):
    """Execute commands step-by-step with validation"""
    execute_interactive_plan(instruction, provider)


def execute_interactive_plan(instruction: str, provider: str):
    planner = StepPlanner(provider)
    validator = StepValidator(provider)
    shell = PersistentShell()

    # Initialize state
    state: ExecutionState = {
        "completed": False,
        "previous_steps": [],
        "current_directory": os.getcwd(),
    }

    while not state["completed"]:
        # Planning phase
        console.print("\n[bold cyan]Model is planning next step...[/]")
        step = planner.generate_next_step(instruction, state)

        # Validation phase
        console.print("[bold cyan]Model is validating step...[/]")
        validation = validator.validate_step(instruction, step, state)

        if validation["approved"]:
            command = validation.get("modification") or step.get("command")

            if not command:
                console.print("[bold red]Error: No valid command to execute!")
                break

            result = shell.execute(command, timeout=step.get("timeout", 60))

            state["previous_steps"].append(
                {
                    "step": step["step"],
                    "timeout": step["timeout"],
                    "command": command,
                    "reason": step["reason"],
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

            console.print(f"\n[bold green]✓ Step {step.get('step', len(state['previous_steps']))} Summary:")
            console.print(f"Command: [cyan]{command}[/]")
            console.print(f"Reason: [magenta]{step.get('reason', 'No reason provided')}[/]")
            console.print(f"Feedback: [yellow]{validation.get('feedback', 'No feedback')}[/]")
            if validation.get("modification"):
                console.print(f"Suggested Modification: [yellow]{validation['modification']}[/]")
            console.print(f"\nOutput: \n[bold green]{result.get('output') or 'No output'}[/]")
            console.print(
                f"Status: [{'green' if result.get('success') else 'red'}]{'Success' if result.get('success') else 'Failed'} (Code: {result.get('exit_code', 'N/A')})[/]"
            )

            state["completed"] = step.get("completed", False) and result.get("success", False)
        else:
            state["previous_steps"].append({
                "step": step["step"],
                "command": "",  # Empty since step was rejected
                "completed": False,
                "feedback": validation["feedback"],
                "reason": step["reason"],
                "output": ""  # Empty since step was not executed
            })
            console.print(f"\n[bold red]✗ Step Rejected:")
            console.print(f"Reason: [white]{validation['feedback']}[/]")
            console.print(
                f"Suggested Modification: [yellow]{validation.get('modification', 'None')}[/]"
            )

        time.sleep(0.4)

    console.print("\n[bold green]✅ Task Completed Successfully!")
    return state


if __name__ == "__main__":
    app()
