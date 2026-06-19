import os
import subprocess
import time
from config import SHELL

MAX_OUTPUT_CHARS = 20000
DEFAULT_TIMEOUT  = 30  # seconds

# Force UTF-8 console I/O in Windows PowerShell so Persian text is not replaced with '?'.
POWERSHELL_UTF8_PREAMBLE = (
    "[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false; "
    "[Console]::InputEncoding = New-Object System.Text.UTF8Encoding $false; "
    "$OutputEncoding = [Console]::OutputEncoding; "
)


def build_shell_command(cmd: str) -> str:
    if SHELL.lower() in ("powershell", "pwsh", "powershell.exe", "pwsh.exe"):
        return POWERSHELL_UTF8_PREAMBLE + cmd
    return cmd


def run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    start = time.time()
    shell_command = build_shell_command(cmd)
    process_environment = os.environ.copy()
    process_environment.setdefault("PYTHONIOENCODING", "utf-8")

    try:
        result = subprocess.run(
            [SHELL, "-NoProfile", "-NonInteractive", "-Command", shell_command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=process_environment,
        )
        duration = round(time.time() - start, 2)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if len(stdout) > MAX_OUTPUT_CHARS:
            stdout = stdout[:MAX_OUTPUT_CHARS] + "\n... [output truncated]"
        if len(stderr) > MAX_OUTPUT_CHARS:
            stderr = stderr[:MAX_OUTPUT_CHARS] + "\n... [truncated]"

        if result.returncode == 0:
            return {
                "status":    "ok",
                "output":    stdout,
                "error":     stderr if stderr else None,
                "exit_code": result.returncode,
                "duration":  duration
            }
        else:
            return {
                "status":    "error",
                "output":    stdout if stdout else None,
                "error":     stderr or f"Process exited with code {result.returncode}",
                "exit_code": result.returncode,
                "duration":  duration
            }

    except subprocess.TimeoutExpired:
        return {
            "status":    "timeout",
            "output":    None,
            "error":     f"Command exceeded {timeout}s timeout and was killed.",
            "exit_code": None,
            "duration":  timeout
        }

    except FileNotFoundError:
        return {
            "status":    "error",
            "output":    None,
            "error":     f"Shell '{SHELL}' not found. Make sure PowerShell is installed and in PATH.",
            "exit_code": None,
            "duration":  0
        }

    except Exception as e:
        return {
            "status":    "error",
            "output":    None,
            "error":     str(e),
            "exit_code": None,
            "duration":  round(time.time() - start, 2)
        }