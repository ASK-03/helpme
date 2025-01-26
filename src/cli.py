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

    state: ExecutionState = {
        "completed": False,
        "previous_steps": [],
        "current_status": "Initializing...",
        "feedback_history": [],
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
            print(command)

            if not command:
                console.print("[bold red]Error: No valid command to execute!")
                break

            result = shell.execute(command)

            state["previous_steps"].append(
                {"step": step["step"], "command": command, "execution_result": result}
            )
            state["current_status"] = result["output"]

            console.print(f"\n[bold green]✓ Step {len(state['previous_steps'])}:")
            console.print(f"Command: [cyan]{command}[/]")
            console.print(f"Output: [yellow]{result['output'] or 'No output'}[/]")
            console.print(
                f"Status: [{'green' if result['success'] else 'red'}]{'Success' if result['success'] else 'Failed'} (Code: {result['exit_code']})[/]"
            )

            state["completed"] = step.get("completed", False) and result["success"]
        else:
            state["feedback_history"].append(validation["feedback"])
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
