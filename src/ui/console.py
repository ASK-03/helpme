from rich.console import Console
from typing import Dict, Any, Optional
from src.core.interfaces import UIProvider

class ConsoleUI(UIProvider):
    def __init__(self):
        self.console = Console()

    def print_planning(self):
        self.console.print("\n[bold cyan]Model is planning next step...[/]")

    def print_validating(self):
        self.console.print("[bold cyan]Model is validating step...[/]")

    def print_step_summary(self, step: Dict[str, Any], validation: Dict[str, Any], result: Dict[str, Any], step_number: int):
        command = validation.get("modification") or step.get("command")
        
        self.console.print(f"\n[bold green]✓ Step {step_number} Summary:")
        self.console.print(f"Command: [cyan]{command}[/]")
        self.console.print(f"Reason: [magenta]{step.get('reason', 'No reason provided')}[/]")
        self.console.print(f"Feedback: [yellow]{validation.get('feedback', 'No feedback')}[/]")
        
        if validation.get("modification"):
            self.console.print(f"Suggested Modification: [yellow]{validation['modification']}[/]")
            
        self.console.print(f"\nOutput: \n[bold green]{result.get('output') or 'No output'}[/]")
        
        status_color = 'green' if result.get('success') else 'red'
        status_text = 'Success' if result.get('success') else 'Failed'
        self.console.print(
            f"Status: [{status_color}]{status_text} (Code: {result.get('exit_code', 'N/A')})[/]"
        )

    def print_step_rejected(self, context: Dict[str, Any], validation: Dict[str, Any]):
        self.console.print(f"\n[bold red]✗ Step Rejected:")
        self.console.print(f"Reason: [white]{validation['feedback']}[/]")
        self.console.print(
            f"Suggested Modification: [yellow]{validation.get('modification', 'None')}[/]"
        )

    def print_error(self, message: str):
        self.console.print(f"[bold red]Error: {message}[/]")

    def print_success(self, message: str):
        self.console.print(f"\n[bold green]✅ {message}")

    def print_status(self, message: str):
        self.console.print(message)
