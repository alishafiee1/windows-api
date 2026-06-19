import time
import uuid

MAX_BUFFER_SIZE = 2 * 1024 * 1024  # 2MB
SESSION_TTL_SECONDS = 600  # 10 minutes

_sessions: dict[str, dict] = {}


def _purge_expired():
    now = time.time()
    expired = [
        edit_id
        for edit_id, session in _sessions.items()
        if now - session["created_at"] > SESSION_TTL_SECONDS
    ]
    for edit_id in expired:
        del _sessions[edit_id]


def generate_edit_id() -> str:
    return uuid.uuid4().hex[:12]


def get_session(edit_id: str) -> dict | None:
    _purge_expired()
    return _sessions.get(edit_id)


def create_session(edit_id: str, loc: str, mode: str) -> dict:
    _purge_expired()
    session = {
        "edit_id": edit_id,
        "loc": loc,
        "mode": mode,
        "old_text": "",
        "new_text": "",
        "old_complete": mode == "edit_lines",
        "start_line": None,
        "end_line": None,
        "created_at": time.time(),
    }
    _sessions[edit_id] = session
    return session


def delete_session(edit_id: str):
    _sessions.pop(edit_id, None)


def set_line_range(session: dict, start_line: int | None, end_line: int | None):
    if start_line is not None:
        session["start_line"] = start_line
    if end_line is not None:
        session["end_line"] = end_line


def append_chunk(
    session: dict,
    chunk_type: str,
    payload: str,
    init_chunk: bool,
) -> str | None:
    field = "old_text" if chunk_type == "old_text" else "new_text"
    if init_chunk:
        session[field] = ""

    current = session[field]
    if len(current) + len(payload) > MAX_BUFFER_SIZE:
        return f"{field} buffer exceeds max size ({MAX_BUFFER_SIZE} bytes)."

    session[field] = current + payload
    return None


def mark_old_complete(session: dict):
    session["old_complete"] = True
