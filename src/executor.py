import subprocess
import re
import os
import fcntl
import time
import select  # Import select for efficient I/O polling
from rich.console import Console

console = Console()


class PersistentShell:
    def __init__(self):
        self.ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        self.process = None
        self._shell_ready = False
        # Buffer to store partial reads between calls
        self.read_buffer = ""
        self._initialize_process()

    def __enter__(self):
        """Allow using the class as a context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Ensure the shell process is closed on exit."""
        self.close()

    def __del__(self):
        """Fallback to close the process when the object is garbage collected."""
        self.close()

    def close(self):
        """Cleanly terminate the shell process."""
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
        """Configure non-blocking I/O for shell process stdout."""
        if self.process and self.process.stdout:
            fd = self.process.stdout.fileno()
            fl = fcntl.fcntl(fd, fcntl.F_GETFL)
            fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def _initialize_process(self):
        """Initialize shell process with proper error handling."""
        try:
            self.process = subprocess.Popen(
                ["bash", "--norc", "--noprofile"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr to stdout
                text=True,
                encoding="utf-8",  # Be explicit about encoding
                # bufsize=0 is deprecated in text mode, remove it
            )
            self._configure_non_blocking()
            self._initialize_shell_environment()
            self._verify_shell_readiness()
        except Exception as e:
            console.print(f"[red]Process initialization failed: {str(e)}[/red]")
            self.close()

    def _initialize_shell_environment(self):
        """Set up clean shell environment."""
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
                self.process.stdin.write(f"{cmd}\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            console.print(f"[red]Failed to initialize shell environment: {e}[/red]")
            self.close()

    def _verify_shell_readiness(self, timeout=2.0):
        """Confirm shell is ready using the efficient select-based read loop."""
        if not self.process:
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
        buffer = self.read_buffer  # Start with any previous leftovers
        self.read_buffer = ""

        try:
            while time.time() - start_time < timeout:
                time_left = timeout - (time.time() - start_time)
                if time_left <= 0:
                    break
                
                # Use select.select to wait for data efficiently
                ready_to_read, _, _ = select.select([fileno], [], [], time_left)

                if not ready_to_read:
                    continue  # select timed out, loop again

                chunk = os.read(fileno, 4096).decode("utf-8")
                if not chunk:  # Process died
                    self.close()
                    break
                
                buffer += chunk

                if readiness_marker in buffer:
                    # Found marker. Save anything *after* it for the next read.
                    _, _, after_marker = buffer.partition(readiness_marker)
                    self.read_buffer = after_marker
                    self._shell_ready = True
                    return

        except (BrokenPipeError, OSError, ValueError):
            self.close()
        except Exception as e:
            console.print(f"[red]Readiness check failed: {str(e)}[/red]")
            self.close()

        # If loop finishes without finding marker
        self.read_buffer = buffer  # Save incomplete buffer
        console.print("[yellow]Shell readiness check timed out[/yellow]")

    def execute(self, command: str, timeout: int = 60) -> dict:
        """Execute command with reliable exit code capture and configurable timeout."""
        result = {"output": "", "exit_code": 1, "success": False}

        if not self._shell_ready or not self.process:
            result["output"] = "Shell not initialized or has died."
            self.close() # Try to re-init
            self._initialize_process()
            return result

        # Generate unique markers
        uid = os.urandom(4).hex()
        exit_marker = f"__EXIT_{uid}__"
        end_marker = f"__END_{uid}__"

        # Build command sequence
        # CRITICAL FIX: Removed the '>&2' redirection.
        cmd_sequence = (
            f"{command}\n"  # Run the command normally
            f"EC=$?\n"
            f"echo '{exit_marker}'\n"
            f"echo $EC\n"
            f"echo '{end_marker}'\n"
        )

        try:
            # Write command
            self.process.stdin.write(cmd_sequence)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as e:
            result["output"] = f"Failed to write command: {e}"
            self.close()
            return result

        # Read output using the efficient select-based loop
        buffer = self.read_buffer  # Start with leftovers from previous read
        self.read_buffer = ""
        fileno = self.process.stdout.fileno()
        start_time = time.time()

        try:
            while time.time() - start_time < timeout:
                time_left = timeout - (time.time() - start_time)
                if time_left <= 0:
                    break
                
                # Wait for data to be available
                ready_to_read, _, _ = select.select([fileno], [], [], time_left)

                if not ready_to_read:
                    continue # select timed out, loop again

                chunk = os.read(fileno, 4096).decode("utf-8")
                if not chunk:  # Process died
                    self.close()
                    result["output"] = self._clean_output(buffer) + "\n[Error: Shell process died]"
                    return result
                
                buffer += chunk

                # Check for markers
                if exit_marker in buffer and end_marker in buffer:
                    # Partition the buffer
                    before_exit, _, remainder = buffer.partition(exit_marker)
                    exit_code_str, _, after_end = remainder.partition(end_marker)

                    # CRITICAL FIX: Save leftovers for the next call
                    self.read_buffer = after_end

                    # Clean and parse exit code
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

        # If we break loop due to timeout
        result["output"] = self._clean_output(buffer) + f"\n[Error: Command timed out after {timeout} seconds]"
        result["exit_code"] = 124  # Standard exit code for timeout
        result["success"] = False
        # Don't close the shell on timeout, just return error
        return result

    def _clean_output(self, text: str) -> str:
        """Clean output while preserving meaningful content"""
        cleaned = self.ansi_escape.sub("", text)
        # Use rstrip() to preserve leading whitespace (indentation)
        # but filter out lines that become empty
        lines = [line.rstrip() for line in cleaned.split("\n")]
        return "\n".join(filter(None, lines))


# Example usage:
if __name__ == "__main__":
    console.print("[cyan]Initializing Persistent Shell...[/cyan]")
    
    # Use 'with' block for automatic cleanup
    with PersistentShell() as shell:
        if not shell._shell_ready:
            console.print("[red]Shell failed to initialize. Exiting.[/red]")
            exit(1)

        console.print("[green]Shell is ready.[/green]")

        console.print("\n[yellow]Running 'echo' test...[/yellow]")
        res = shell.execute("echo 'Hello World'")
        console.print(res)

        console.print("\n[yellow]Running 'ls -la' test...[/yellow]")
        res = shell.execute("ls -la")
        console.print(res)

        console.print("\n[yellow]Running failing command test...[/yellow]")
        res = shell.execute("cat /nonexistent/file")
        console.print(res)

        console.print(f"\n[yellow]Running long 'find' command with 5 min timeout...[/yellow]")
        # Now you can pass a longer timeout for slow commands!
        res = shell.execute(
            'find / -type d -iname "codeforces" 2>/dev/null', 
            timeout=300
        )
        console.print(res)
        
        console.print("\n[yellow]Running another 'echo' to test buffer...[/yellow]")
        res = shell.execute("echo 'Buffer test successful'")
        console.print(res)

    console.print("\n[cyan]Shell closed.[/cyan]")
