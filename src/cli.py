import typer
from src.main import main

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
    main(instruction, provider)

if __name__ == "__main__":
    app()
