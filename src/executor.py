# executor.py
import subprocess
import re
import os
import fcntl
import time
from rich.console import Console

console = Console()


class PersistentShell:
    def __init__(self):
        self.ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.process = None
        self._shell_ready = False
        self._initialize_process()

    def _configure_non_blocking(self):
        """Configure non-blocking I/O for shell process"""
        if self.process and self.process.stdout:
            fd = self.process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def _initialize_process(self):
        """Initialize shell process with proper error handling"""
        try:
            self.process = subprocess.Popen(
                ["bash", "--norc", "--noprofile"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=0,
                text=True,
            )
            self._configure_non_blocking()  # Now properly defined
            self._initialize_shell_environment()
            self._verify_shell_readiness()
        except Exception as e:
            console.print(f"[red]Process initialization failed: {str(e)}[/red]")
            self.process = None

    def _initialize_shell_environment(self):
        """Set up clean shell environment"""
        init_sequence = [
            "export PS1=''",
            "unset PROMPT_COMMAND",
            "export TERM=dumb",
            "stty -echo",
            "true",
        ]

        try:
            for cmd in init_sequence:
                self.process.stdin.write(f"{cmd}\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            self.process = None

    def _verify_shell_readiness(self):
        """Confirm shell is ready to receive commands"""
        test_cmd = "echo '__SHELL_READY__'\n"
        start_time = time.time()
        response = []

        try:
            self.process.stdin.write(test_cmd)
            self.process.stdin.flush()

            while time.time() - start_time < 2:
                try:
                    chunk = os.read(self.process.stdout.fileno(), 1024).decode()
                    response.append(chunk)
                    if "__SHELL_READY__" in "".join(response):
                        self._shell_ready = True
                        return
                except BlockingIOError:
                    time.sleep(0.1)

            console.print("[yellow]Shell readiness check timed out[/yellow]")
        except Exception as e:
            console.print(f"[red]Readiness check failed: {str(e)}[/red]")

    def execute(self, command: str) -> dict:
        """Execute command with reliable exit code capture"""
        result = {"output": "", "exit_code": 1, "success": False}

        if not self._shell_ready:
            result["output"] = "Shell not initialized"
            return result

        try:
            # Generate unique markers
            uid = os.urandom(4).hex()
            exit_marker = f"__EXIT_{uid}__"
            end_marker = f"__END_{uid}__"

            # Build command sequence
            cmd_sequence = (
                f"{command} >&2\n"  # Send all output to stderr
                f"EC=$?\n"
                f"echo '{exit_marker}'\n"
                f"echo $EC\n"
                f"echo '{end_marker}'\n"
            )

            # Write command
            self.process.stdin.write(cmd_sequence)
            self.process.stdin.flush()

            # Read output
            output_buffer = []
            exit_code = 1
            in_exit_code = False
            start_time = time.time()

            while time.time() - start_time < 60:
                try:
                    chunk = os.read(self.process.stdout.fileno(), 1024).decode()
                    if not chunk:
                        time.sleep(0.2)
                        continue

                    output_buffer.append(chunk)
                    buffer_str = "".join(output_buffer)

                    # Check for markers
                    if exit_marker in buffer_str and end_marker in buffer_str:
                        # Split output components
                        before_exit, _, remainder = buffer_str.partition(exit_marker)
                        exit_code_str, _, after_end = remainder.partition(end_marker)

                        # Clean and parse exit code
                        result["output"] = self._clean_output(before_exit)
                        try:
                            exit_code = int(exit_code_str.strip())
                        except ValueError:
                            exit_code = 1
                        break

                except BlockingIOError:
                    time.sleep(0.05)

            result["exit_code"] = exit_code
            result["success"] = exit_code == 0
            return result

        except Exception as e:
            result["output"] = f"Execution error: {str(e)}"
            return result

    def _clean_output(self, text: str) -> str:
        """Clean output while preserving meaningful content"""
        cleaned = self.ansi_escape.sub("", text)
        lines = [line.rstrip() for line in cleaned.split("\n")]
        return "\n".join(filter(None, lines))
