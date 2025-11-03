# HelpMe

## Description

HelpMe is a powerful terminal-based CLI tool designed to help you accomplish user-defined Linux tasks by automatically generating and executing step-by-step commands. The tool uses advanced AI Agents to intelligently generate, validate, and verify each command, ensuring accuracy, safety, and efficiency in completing tasks on the command line.

- [Demo Video v1](https://www.loom.com/share/a79bb41eb3f542ad91d388d41f27bb12?sid=51aa2840-b88a-4fc1-8c0a-09932dde9786)
- [Demo Video v2](https://drive.google.com/file/d/1jtbwRMCnVWzH4I1aHI2AJHSxyU9lEHyH/view?usp=sharing)

## Features

- **Automatic Plan Generation**: Converts user instructions into clear, sequential commands for the Linux terminal, making it easy to accomplish complex tasks.
- **Intelligent Plan Verification**: Each generated command is verified to ensure it aligns with the user’s instructions and incorporates prior feedback before execution.
- **Flexible Execution Modes**: Choose between using a local model (Ollama's llama 3.1) or an online API with the Gemini LLM by Google.
- **Robust Error Handling**: Errors during command execution are caught, and the tool provides feedback without executing subsequent commands.

## Requirements

- **Python**: 3.8 or higher
- **Python Packages**: Install dependencies listed in `requirements.txt`
- **API Access**: A Gemini/OpenAI API key for online execution or Ollama for offline execution.

## Getting Started

1. **Fork and Clone the Repository**

   - Fork the HelpMe repository to your GitHub account.
   - Clone your forked repository locally:
     ```bash
     git clone https://github.com/{YOUR-USERNAME}/helpme
     cd helpme
     ```

2. **Install Dependencies**

   - Install necessary packages by running:
     ```bash
     pip install -r requirements.txt
     ```

3. **Set Up API Key**
   - Add your `GEMINI_API_KEY` or `OPENAI_API_KEY` in a `.env` file as shown in `.env.example`.

## Usage

To use the HelpMe CLI tool, you can either run the Python script directly or create an executable for easier access.

### Run Directly

Run the tool with a user instruction. Here’s an example:

```bash
python helpme.py "create a folder named 'hello'" --provider gemini/openai/deepseek/ollama
```

### Create an Executable (Optional)

For easier access, you can create a standalone executable with **PyInstaller**.

1. Build the executable:
   ```bash
   pyinstaller --onefile src/helpme.py
   ```
2. Move the executable to your system path (e.g., `/usr/bin`) for global access:
   ```bash
   sudo cp dist/helpme /usr/bin/helpme
   ```

Now you can run `helpme` directly from the terminal.

### Example Usage

Use `helpme` to generate and execute a plan based on a user-defined instruction:

```bash
helpme "create a new directory named 'mydir'" --provider gemini
```

Options:

- `instruction` (str): The instruction you want to turn into commands.
- `--provider` (optional): Use the Gemini/OpenAI/Deepseek if you have internet access. If omitted, the tool defaults to using Ollama's Llama 3.1 model.

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository.
2. Create a new branch.
3. Make your changes and commit them.
4. Submit a pull request.

Please feel free to open issues for any bugs or feature requests.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Authors

- [Abhishek Singh Kushwaha](https://ask03.vercel.app)