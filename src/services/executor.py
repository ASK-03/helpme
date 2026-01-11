import subprocess
import re
import os
import fcntl
import time
import select
from typing import Dict, Any, Optional

from rich.console import Console

from src.core.interfaces import Executor

# We will keep local Console for now, or move printing to UI provider later.
# The original executor printed errors. I'll keep it for now but ideally should return errors or use a logger.
console = Console()

class PersistentShell(Executor):
    def __init__(self):
        self.ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.process: Optional[subprocess.Popen] = None
        self._shell_ready = False
        self.read_buffer = ""
        self._initialize_process()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except Exception as e:
                console.print(f"[red]Error closing shell: {str(e)}[/red]")
        self.process = None
        self._shell_ready = False

    def _configure_non_blocking(self):
        if self.process and self.process.stdout:
            fd = self.process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def _initialize_process(self):
        try:
            self.process = subprocess.Popen(
                ["bash", "--norc", "--noprofile"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
            )
            self._configure_non_blocking()
            self._initialize_shell_environment()
            self._verify_shell_readiness()
        except Exception as e:
            console.print(f"[red]Process initialization failed: {str(e)}[/red]")
            self.close()

    def _initialize_shell_environment(self):
        if not self.process:
            return
            
        init_sequence = [
            "export PS1=''",
            "unset PROMPT_COMMAND",
            "export TERM=dumb",
            "stty -echo",
            "true",
        ]

        try:
            for cmd in init_sequence:
                if self.process.stdin:
                    self.process.stdin.write(f"{cmd}\n")
            if self.process.stdin:
                self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            console.print(f"[red]Failed to initialize shell environment: {e}[/red]")
            self.close()

    def _verify_shell_readiness(self, timeout=2.0):
        if not self.process or not self.process.stdin or not self.process.stdout:
            return

        readiness_marker = "__SHELL_READY__"
        
        try:
            self.process.stdin.write(f"echo '{readiness_marker}'\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            console.print(f"[red]Failed to write readiness check: {e}[/red]")
            self.close()
            return

        fileno = self.process.stdout.fileno()
        start_time = time.time()
        buffer = self.read_buffer
        self.read_buffer = ""

        try:
            while time.time() - start_time < timeout:
                time_left = timeout - (time.time() - start_time)
                if time_left <= 0:
                    break
                
                ready_to_read, _, _ = select.select([fileno], [], [], time_left)

                if not ready_to_read:
                    continue

                chunk = os.read(fileno, 4096).decode("utf-8")
                if not chunk:
                    self.close()
                    break
                
                buffer += chunk

                if readiness_marker in buffer:
                    _, _, after_marker = buffer.partition(readiness_marker)
                    self.read_buffer = after_marker
                    self._shell_ready = True
                    return

        except (BrokenPipeError, OSError, ValueError):
            self.close()
        except Exception as e:
            console.print(f"[red]Readiness check failed: {str(e)}[/red]")
            self.close()

        self.read_buffer = buffer
        console.print("[yellow]Shell readiness check timed out[/yellow]")

    def execute(self, command: str, timeout: int = 60) -> Dict[str, Any]:
        result = {"output": "", "exit_code": 1, "success": False}

        if not self._shell_ready or not self.process or not self.process.stdin:
            result["output"] = "Shell not initialized or has died."
            self.close()
            self._initialize_process()
            return result

        uid = os.urandom(4).hex()
        exit_marker = f"__EXIT_{uid}__"
        end_marker = f"__END_{uid}__"

        cmd_sequence = (
            f"{command}\n"
            f"EC=$?\n"
            f"echo '{exit_marker}'\n"
            f"echo $EC\n"
            f"echo '{end_marker}'\n"
        )

        try:
            self.process.stdin.write(cmd_sequence)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            result["output"] = f"Failed to write command: {e}"
            self.close()
            return result

        buffer = self.read_buffer
        self.read_buffer = ""
        fileno = self.process.stdout.fileno() # type: ignore
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                time_left = timeout - (time.time() - start_time)
                if time_left <= 0:
                    break
                
                ready_to_read, _, _ = select.select([fileno], [], [], time_left)

                if not ready_to_read:
                    continue

                chunk = os.read(fileno, 4096).decode("utf-8")
                if not chunk:
                    self.close()
                    result["output"] = self._clean_output(buffer) + "\n[Error: Shell process died]"
                    return result
                
                buffer += chunk

                if exit_marker in buffer and end_marker in buffer:
                    before_exit, _, remainder = buffer.partition(exit_marker)
                    exit_code_str, _, after_end = remainder.partition(end_marker)

                    self.read_buffer = after_end

                    result["output"] = self._clean_output(before_exit)
                    try:
                        exit_code = int(exit_code_str.strip())
                    except ValueError:
                        console.print(f"[yellow]Warning: Could not parse exit code: {exit_code_str!r}[/yellow]")
                        exit_code = 1
                        
                    result["exit_code"] = exit_code
                    result["success"] = exit_code == 0
                    return result

        except (BrokenPipeError, OSError, ValueError):
            result["output"] = self._clean_output(buffer) + "\n[Error: Shell process died during read]"
            self.close()
            return result
        except Exception as e:
            result["output"] = self._clean_output(buffer) + f"\n[Error: {e}]"
            self.close()
            return result

        result["output"] = self._clean_output(buffer) + f"\n[Error: Command timed out after {timeout} seconds]"
        result["exit_code"] = 124
        result["success"] = False
        return result

    def _clean_output(self, text: str) -> str:
        cleaned = self.ansi_escape.sub("", text)
        lines = [line.rstrip() for line in cleaned.split("\n")]
        return "\n".join(filter(None, lines))
