
with open('/home/user/windows-cmd-api/core/runner.py', 'w') as f:
    f.write("""import subprocess
import time
from config import SHELL

MAX_OUTPUT_CHARS = 20000
DEFAULT_TIMEOUT = 30  # seconds

def run_command(cmd: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    \"\"\"
    Runs a command in PowerShell and returns result dict:
    { status, output, error, exit_code, duration }
    \"\"\"
    start = time.time()

    try:
        result = subprocess.run(
            [SHELL, "-NoProfile", "-NonInteractive", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        duration = round(time.time() - start, 2)

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Truncate long outputs
        if len(stdout) > MAX_OUTPUT_CHARS:
            stdout = stdout[:MAX_OUTPUT_CHARS] + "\\n... [output truncated]"
        if len(stderr) > MAX_OUTPUT_CHARS:
            stderr = stderr[:MAX_OUTPUT_CHARS] + "\\n... [truncated]"

        if result.returncode == 0:
            return {
                "status": "ok",
                "output": stdout,
                "error": stderr if stderr else None,
                "exit_code": result.returncode,
                "duration": duration
            }
        else:
            return {
                "status": "error",
                "output": stdout if stdout else None,
                "error": stderr or f"Process exited with code {result.returncode}",
                "exit_code": result.returncode,
                "duration": duration
            }

    except subprocess.TimeoutExpired:
        return {
            "status": "timeout",
            "output": None,
            "error": f"Command exceeded {timeout}s timeout and was killed.",
            "exit_code": None,
            "duration": timeout
        }

    except FileNotFoundError:
        return {
            "status": "error",
            "output": None,
            "error": f"Shell '{SHELL}' not found. Make sure PowerShell is installed and in PATH.",
            "exit_code": None,
            "duration": 0
        }

    except Exception as e:
        return {
            "status": "error",
            "output": None,
            "error": str(e),
            "exit_code": None,
            "duration": round(time.time() - start, 2)
        }
""")

print("Done")