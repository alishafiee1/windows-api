import atexit
import os
import signal
import subprocess
import sys
import time

PID_FILE_PATH = os.path.join("data", "server.pid")


def _is_windows() -> bool:
    return sys.platform == "win32"


def _subprocess_flags() -> int:
    if _is_windows() and hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def is_process_running(process_id: int) -> bool:
    if process_id <= 0:
        return False

    if _is_windows():
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {process_id}"],
            capture_output=True,
            text=True,
            creationflags=_subprocess_flags(),
        )
        return str(process_id) in result.stdout

    try:
        os.kill(process_id, 0)
    except OSError:
        return False
    return True


def find_process_ids_listening_on_port(port: int) -> list[int]:
    process_ids: set[int] = set()

    if _is_windows():
        result = subprocess.run(
            ["netstat", "-ano"],
            capture_output=True,
            text=True,
            creationflags=_subprocess_flags(),
        )
        port_suffix = f":{port}"
        for line in result.stdout.splitlines():
            if "LISTENING" not in line or port_suffix not in line:
                continue
            parts = line.split()
            if not parts:
                continue
            try:
                process_ids.add(int(parts[-1]))
            except ValueError:
                continue
    else:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                process_ids.add(int(line))

    return sorted(process_ids)


def terminate_process(process_id: int) -> bool:
    current_process_id = os.getpid()
    if process_id in (0, current_process_id):
        return False

    if _is_windows():
        result = subprocess.run(
            ["taskkill", "/PID", str(process_id), "/F"],
            capture_output=True,
            text=True,
            creationflags=_subprocess_flags(),
        )
        return result.returncode == 0

    try:
        os.kill(process_id, signal.SIGTERM)
        return True
    except OSError:
        return False


def read_stored_process_id() -> int | None:
    if not os.path.exists(PID_FILE_PATH):
        return None

    try:
        with open(PID_FILE_PATH, "r", encoding="utf-8") as pid_file:
            raw_value = pid_file.read().strip()
        return int(raw_value)
    except (OSError, ValueError):
        return None


def write_stored_process_id(process_id: int) -> None:
    os.makedirs(os.path.dirname(PID_FILE_PATH), exist_ok=True)
    with open(PID_FILE_PATH, "w", encoding="utf-8") as pid_file:
        pid_file.write(str(process_id))


def remove_stored_process_id() -> None:
    try:
        if os.path.exists(PID_FILE_PATH):
            os.remove(PID_FILE_PATH)
    except OSError:
        pass


def free_port(port: int) -> list[int]:
    stopped_process_ids: list[int] = []

    for process_id in find_process_ids_listening_on_port(port):
        if terminate_process(process_id):
            stopped_process_ids.append(process_id)

    if stopped_process_ids:
        time.sleep(0.3)

    return stopped_process_ids


def stop_previous_server_instance(port: int) -> list[int]:
    stopped_process_ids: list[int] = []
    stored_process_id = read_stored_process_id()

    if stored_process_id and is_process_running(stored_process_id):
        if terminate_process(stored_process_id):
            stopped_process_ids.append(stored_process_id)
            time.sleep(0.3)

    for process_id in free_port(port):
        if process_id not in stopped_process_ids:
            stopped_process_ids.append(process_id)

    remove_stored_process_id()
    return stopped_process_ids


def prepare_server_start(port: int) -> list[int]:
    stopped_process_ids = stop_previous_server_instance(port)
    write_stored_process_id(os.getpid())
    return stopped_process_ids


def _handle_shutdown_signal(signum, frame):
    remove_stored_process_id()
    raise SystemExit(0)


def register_server_shutdown() -> None:
    atexit.register(remove_stored_process_id)

    signal.signal(signal.SIGINT, _handle_shutdown_signal)
    signal.signal(signal.SIGTERM, _handle_shutdown_signal)

    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, _handle_shutdown_signal)
