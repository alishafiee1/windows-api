import uuid
import time
from config import CONFIRM_TIMEOUT

# { token: { "cmd": str, "created_at": float, "status": "pending"|"approved"|"rejected" } }
_store: dict = {}


def create_token(cmd: str) -> str:
    token = str(uuid.uuid4())[:8]
    _store[token] = {
        "cmd": cmd,
        "created_at": time.time(),
        "status": "pending"
    }
    return token


def get_token(token: str) -> dict | None:
    entry = _store.get(token)
    if not entry:
        return None
    if time.time() - entry["created_at"] > CONFIRM_TIMEOUT:
        del _store[token]
        return None
    return entry


def approve_token(token: str) -> str | None:
    entry = get_token(token)
    if not entry:
        return None
    _store[token]["status"] = "approved"
    return entry["cmd"]


def reject_token(token: str) -> bool:
    entry = get_token(token)
    if not entry:
        return False
    _store[token]["status"] = "rejected"
    return True


def delete_token(token: str):
    _store.pop(token, None)