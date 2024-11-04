import os
import json
import subprocess
from dotenv import load_dotenv
import ollama
import typer
from typing import Literal, Dict, Any
from rich.console import Console
import google.generativeai as genai
from google.generativeai import GenerationConfig

load_dotenv()

app = typer.Typer()

# Constants
MODEL = "llama3.1"
FORMAT = "json"
OPTIONS = {"temperature": 0, "max_tokens": 100}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
generation_config = GenerationConfig(
    temperature=0,
    top_p=1.0,
    top_k=50,
    max_output_tokens=2048,
    response_mime_type="application/json",
)
gemini_model = genai.GenerativeModel(
    "gemini-1.5-flash", generation_config=generation_config
)

# Initialize the console for rich output
console = Console()


def call_llm(
    prompt: str,
    model=MODEL,
    format: Literal["", "json"] = FORMAT,
    options=OPTIONS,
    online: bool = False,
) -> Dict[str, Any]:
    """
    Calls the language model with the provided prompt and returns the parsed JSON response.
    """
    if not online:
        response = ollama.generate(
            model=model, prompt=prompt, format=format, options=options
        )
        return json.loads(response["response"])
    else:
        response = gemini_model.generate_content(prompt)
        return json.loads(response.text)


def get_planner_prompt(instruction: str, plan: str, feedback: str) -> str:
    """
    Generates a prompt for the language model to create a step-by-step plan.
    """
    prompt = f"""
    You are an AI assistant tasked with generating a detailed, step-by-step plan to accomplish the user's instruction. 
    Break down the instruction into small, actionable steps that are clear and concise. 
    The commands will be executed in a terminal in the same system. 
    - Do not provide commands to "Reboot the system" or "Shutdown the system." Instead, if the instruction is to reboot or shutdown the system, 
      provide an alert using the 'echo' command and direct the user to reboot or shutdown.
    - There is no need for a step to open the terminal.
    - Each step should logically follow the previous one, ensuring that subsequent commands utilize the outputs of earlier commands where relevant.
    - When using `find` command to search for files or directories, ensure that the search is limited to the necessary directories. If the directory is not specified, the search should be limited to the user's home directory.
    
    System: Linux
    User Instruction: {instruction}
    Previous Generated Plan: {plan}
    Feedback to the plan: {feedback}
    
    Format your response as a JSON object with the following structure:
    {{
        "plan": [
            {{
                "step": "step 1...",
                "command": "command 1..."
            }},
            {{
                "step": "step 2, using output from step 1",
                "command": "command 2 that uses output from step 1"
            }},
            ...
        ]
    }}

    Example 1:
    Instruction: "Open brave browser"
    Plan: {{
        "plan": [
            {{
                "step": "Check if Brave browser is installed and store the result",
                "command": "BRAVE_PATH=$(which brave)"
            }},
            {{
                "step": "If Brave is installed, open Brave browser; else print a message",
                "command": "if [ -x \"$BRAVE_PATH\" ]; then brave; else echo 'Brave is not installed.'; fi"
            }}
        ]
    }}

    Example 2:
    Instruction: "Create a new directory named 'mydir'"
    Plan: {{
        "plan": [
            {{
                "step": "Check if 'mydir' exists",
                "command": "if [ -d mydir ]; then echo 'Directory already exists'; else echo 'Directory does not exist'; fi"
            }},
            {{
                "step": "If 'mydir' does not exist, create 'mydir'",
                "command": "if [ ! -d mydir ]; then mkdir mydir; else echo 'Directory already exists'; fi"
            }}
        ]
    }}
    """
    return prompt


def get_verifier_prompt(instruction: str, plan: str, feedback: str) -> str:
    """
    Generates a prompt for the language model to verify the generated plan.
    """
    prompt = f"""
    You are an AI verifier assigned to evaluate a new step-by-step plan based on the provided user instruction and previous feedback. 
    Each step in the plan will be executed sequentially, and the commands may use outputs from the previous steps. 
    Your goal is to review the new plan for alignment with the user’s needs and to ensure clarity and efficiency in the steps.

    If the new plan effectively fulfills the user instruction and incorporates previous feedback, respond with "APPROVED." 
    If there are still issues or necessary improvements, provide specific, concise feedback that focuses on the changes made since the last review. 
    Only indicate "NOT_APPROVED" if a step is genuinely unnecessary or if the new plan does not comply with the user instruction.

    System: Linux
    User Instruction: {instruction}
    Your Previous Feedback: {feedback}
    New Generated Plan: {plan}

    Format your response as a JSON object with the following structure:
    {{
        "plan": [
            {{
                "step": "step instructions...",
                "status": "Enum('APPROVED', 'NOT_APPROVED')",
                "feedback": "Provide clear and constructive feedback here or just write 'APPROVED' if everything is satisfactory."
            }},
            {{
                "step": "step that uses output from the previous step...",
                "status": "Enum('APPROVED', 'NOT_APPROVED')",
                "feedback": "Provide clear and constructive feedback here or just write 'APPROVED' if everything is satisfactory."
            }}
        ]
    }}
    """
    return prompt


def execute_plan(plan: Dict[str, Any]) -> None:
    """
    Executes the commands in the generated plan using the system shell.
    """
    commands = "; ".join(step["command"] for step in plan["plan"])
    try:
        subprocess.run(commands, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing commands: {e}")


@app.command()
def run(instruction: str, online: bool = False):
    """
    Main function to generate and execute a step-by-step plan based on user instruction.
    """
    feedback: str = ""
    plan = {}
    PLAN_APPROVED = False

    while not PLAN_APPROVED:
        # Indicate planning phase
        with console.status("[bold blue]Planning...") as status:
            plan = call_llm(
                get_planner_prompt(instruction, json.dumps(plan, indent=4), feedback),
                online=online,
            )
            console.print("[bold] Generated Plan:")
            for i, step in enumerate(plan["plan"]):
                console.print(f"\tStep {i}: " + step["step"])
                console.print("\t\tCommand: " + step["command"])

        # Indicate verification phase
        with console.status("[bold yellow]Verifying...") as status:
            verify = call_llm(
                get_verifier_prompt(instruction, json.dumps(plan, indent=4), feedback),
                online=online,
            )
            console.print("[bold] Feedback:")
            for i, step in enumerate(verify["plan"]):
                console.print(f"\tStep {i}: " + step["step"])
                console.print("\t\tStatus: " + step["status"])
                console.print("\t\tFeedback: " + step["feedback"])

            feedback_messages = []
            all_steps_approved = True

            for step in verify["plan"]:
                if step["status"] == "NOT_APPROVED":
                    feedback_messages.append(f"{step['step']}: {step['feedback']}")
                    all_steps_approved = False

            if feedback_messages:
                feedback = " | ".join(feedback_messages)  # Aggregate feedback messages

            PLAN_APPROVED = all_steps_approved

    execute_plan(plan)


if __name__ == "__main__":
    app()
