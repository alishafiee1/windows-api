from flask import Blueprint, request, jsonify
from pathlib import Path
from core import edit_buffer

file_bp = Blueprint('file', __name__)

MAX_CHUNK_CHARS = 1800  # safe limit for GET chunk size
MAX_READ_SIZE = 2 * 1024 * 1024  # 2MB


def _get_loc():
    return (request.args.get('loc') or request.args.get('path') or '').strip()


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() == 'true'


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value == '':
        return None
    return int(value)


def _safe_path(raw: str):
    """Validate and return a Path. Only absolute Windows paths allowed."""
    p = Path(raw)
    if not p.is_absolute():
        return None, "Only absolute paths are allowed (e.g. D:\\project\\file.md)"
    return p, None


def _load_file(p: Path, not_found_label: str | None = None) -> tuple[str | None, str | None, int]:
    label = not_found_label or str(p)
    if not p.exists():
        return None, f"File not found: {label}", 404
    if not p.is_file():
        return None, "Path is a directory, not a file.", 400
    file_size = p.stat().st_size
    if file_size > MAX_READ_SIZE:
        return None, (
            f"File too large ({file_size} bytes). Max allowed: {MAX_READ_SIZE} bytes."
        ), 413
    try:
        return p.read_text(encoding='utf-8-sig'), None, 200
    except Exception as e:
        return None, str(e), 500


def _save_file(p: Path, content: str) -> str | None:
    try:
        p.write_text(content, encoding='utf-8')
        return None
    except Exception as e:
        return str(e)


def _apply_replace_text(content: str, old_text: str, new_text: str) -> tuple[str | None, str | None, int]:
    count = content.count(old_text)
    if count == 0:
        return None, "old_text not found", 404
    if count > 1:
        return None, f"old_text matched {count} times; provide more context", 409
    return content.replace(old_text, new_text, 1), None, 200


def _apply_edit_lines(
    lines: list[str],
    start_line: int,
    end_line: int,
    new_text: str,
) -> tuple[list[str] | None, str | None, int]:
    if start_line < 1 or end_line < start_line:
        return None, "Invalid line range", 400
    if start_line > len(lines):
        return None, f"start_line {start_line} is out of bounds (file has {len(lines)} lines)", 400

    end_line = min(end_line, len(lines))
    replacement = new_text.splitlines(keepends=True)
    if new_text and not replacement:
        replacement = [new_text]

    new_lines = lines[: start_line - 1] + replacement + lines[end_line:]
    return new_lines, None, 200


def _commit_replace_text(p: Path, raw_path: str, old_text: str, new_text: str):
    content, load_err, status = _load_file(p, raw_path)
    if load_err:
        return jsonify({"status": "error", "error": load_err}), status

    updated, edit_err, edit_status = _apply_replace_text(content, old_text, new_text)
    if edit_err:
        return jsonify({"status": "error", "error": edit_err}), edit_status

    save_err = _save_file(p, updated)
    if save_err:
        return jsonify({"status": "error", "error": save_err}), 500

    return jsonify({
        "status": "ok",
        "loc": str(p),
        "mode": "replace_text",
        "total_lines": len(updated.splitlines()),
        "message": "File updated successfully.",
    }), 200


def _commit_edit_lines(p: Path, raw_path: str, start_line: int, end_line: int, new_text: str):
    content, load_err, status = _load_file(p, raw_path)
    if load_err:
        return jsonify({"status": "error", "error": load_err}), status

    lines = content.splitlines(keepends=True)
    if content and not lines:
        lines = [content]

    updated_lines, edit_err, edit_status = _apply_edit_lines(
        lines, start_line, end_line, new_text,
    )
    if edit_err:
        return jsonify({"status": "error", "error": edit_err}), edit_status

    updated_content = ''.join(updated_lines)
    save_err = _save_file(p, updated_content)
    if save_err:
        return jsonify({"status": "error", "error": save_err}), 500

    return jsonify({
        "status": "ok",
        "loc": str(p),
        "mode": "edit_lines",
        "start_line": start_line,
        "end_line": min(end_line, len(lines)),
        "total_lines": len(updated_lines),
        "message": "File updated successfully.",
    }), 200


def _handle_edit_fast_path(p: Path, raw_path: str, mode: str):
    if mode == 'replace_text':
        if 'old_text' not in request.args or 'new_text' not in request.args:
            return jsonify({
                "status": "error",
                "error": "Missing 'old_text' or 'new_text' parameter.",
            }), 400
        return _commit_replace_text(
            p, raw_path, request.args.get('old_text', ''), request.args.get('new_text', ''),
        )

    if 'start_line' not in request.args or 'end_line' not in request.args:
        return jsonify({
            "status": "error",
            "error": "Missing 'start_line' or 'end_line' parameter.",
        }), 400

    try:
        start_line = int(request.args.get('start_line'))
        end_line = int(request.args.get('end_line'))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "error": "start_line and end_line must be integers."}), 400

    new_text = request.args.get('new_text', '')
    return _commit_edit_lines(p, raw_path, start_line, end_line, new_text)


def _handle_edit_stream(p: Path, raw_path: str, mode: str):
    chunk_type = (request.args.get('chunk_type') or '').strip().lower()
    if chunk_type not in ('old_text', 'new_text'):
        return jsonify({"status": "error", "error": "chunk_type must be 'old_text' or 'new_text'."}), 400

    if mode == 'edit_lines' and chunk_type == 'old_text':
        return jsonify({"status": "error", "error": "edit_lines mode only accepts chunk_type=new_text."}), 400

    payload = request.args.get('payload', '')
    init_chunk = _parse_bool(request.args.get('init_chunk'))
    finalize = _parse_bool(request.args.get('finalize'))

    edit_id = (request.args.get('edit_id') or '').strip()
    if not edit_id:
        edit_id = edit_buffer.generate_edit_id()

    session = edit_buffer.get_session(edit_id)
    if session is None:
        session = edit_buffer.create_session(edit_id, raw_path, mode)
    elif session['loc'] != raw_path or session['mode'] != mode:
        return jsonify({"status": "error", "error": "edit_id session mismatch for loc or mode."}), 400

    try:
        start_line = _parse_optional_int(request.args.get('start_line'))
        end_line = _parse_optional_int(request.args.get('end_line'))
    except ValueError:
        return jsonify({"status": "error", "error": "start_line and end_line must be integers."}), 400

    if mode == 'edit_lines':
        edit_buffer.set_line_range(session, start_line, end_line)

    buffer_err = edit_buffer.append_chunk(session, chunk_type, payload, init_chunk)
    if buffer_err:
        return jsonify({"status": "error", "error": buffer_err}), 413

    if chunk_type == 'old_text' and finalize:
        edit_buffer.mark_old_complete(session)

    if chunk_type == 'new_text' and mode == 'replace_text' and not session['old_complete']:
        return jsonify({
            "status": "error",
            "error": "old_text buffer must be finalized before sending new_text chunks.",
        }), 400

    if not finalize:
        buffered = len(session['old_text'] if chunk_type == 'old_text' else session['new_text'])
        return jsonify({
            "status": "ok",
            "edit_id": edit_id,
            "chunk_type": chunk_type,
            "buffered_chars": buffered,
            "finalized": False,
            "message": "Chunk buffered.",
        }), 200

    if chunk_type == 'old_text':
        return jsonify({
            "status": "ok",
            "edit_id": edit_id,
            "chunk_type": chunk_type,
            "buffered_chars": len(session['old_text']),
            "finalized": True,
            "message": "old_text buffer complete. Send new_text chunks next.",
        }), 200

    if mode == 'replace_text':
        response = _commit_replace_text(p, raw_path, session['old_text'], session['new_text'])
        edit_buffer.delete_session(edit_id)
        return response

    if session['start_line'] is None or session['end_line'] is None:
        edit_buffer.delete_session(edit_id)
        return jsonify({
            "status": "error",
            "error": "Missing 'start_line' or 'end_line' parameter.",
        }), 400

    response = _commit_edit_lines(
        p, raw_path, session['start_line'], session['end_line'], session['new_text'],
    )
    edit_buffer.delete_session(edit_id)
    return response


def _normalize_sync_method(raw_method: str) -> str | None:
    method = raw_method.strip().lower()
    if method in ('init_sync', 'overwrite'):
        return 'init_sync'
    if method in ('add_chunk', 'append'):
        return 'add_chunk'
    return None


def _get_sync_params():
    raw_path = _get_loc()
    payload = request.args.get('payload')
    if payload is None:
        payload = request.args.get('content', '')

    raw_method = request.args.get('method')
    if raw_method is None:
        raw_method = request.args.get('mode', 'add_chunk')
    sync_method = _normalize_sync_method(raw_method)

    finalize_raw = request.args.get('finalize')
    if finalize_raw is None:
        finalize_raw = request.args.get('done', 'false')
    finalize = finalize_raw.strip().lower() == 'true'

    return raw_path, payload, sync_method, finalize


@file_bp.route('/file/read', methods=['GET'])
def file_read():
    r"""
    Read a text file and return its content.
    GET /file/read?loc=D:\project\file.md
    Optional: ?chunk=1&size=1800  — returns a specific chunk (1-based index)
    """
    raw_path = _get_loc()
    if not raw_path:
        return jsonify({"status": "error", "error": "Missing 'loc' parameter."}), 400

    p, err = _safe_path(raw_path)
    if err:
        return jsonify({"status": "error", "error": err}), 400

    content, load_err, status = _load_file(p, raw_path)
    if load_err:
        return jsonify({"status": "error", "error": load_err}), status

    chunk_index = request.args.get('chunk', None)
    chunk_size = int(request.args.get('size', MAX_CHUNK_CHARS))

    if chunk_index is not None:
        chunk_index = int(chunk_index)
        total_chars = len(content)
        total_chunks = max(1, -(-total_chars // chunk_size))
        start = (chunk_index - 1) * chunk_size
        end = start + chunk_size
        chunk_content = content[start:end]
        return jsonify({
            "status": "ok",
            "loc": str(p),
            "chunk": chunk_index,
            "total_chunks": total_chunks,
            "total_chars": total_chars,
            "has_more": chunk_index < total_chunks,
            "content": chunk_content
        })

    total_chars = len(content)
    total_chunks = max(1, -(-total_chars // MAX_CHUNK_CHARS))
    return jsonify({
        "status": "ok",
        "loc": str(p),
        "total_chars": total_chars,
        "total_chunks": total_chunks,
        "chunk_size": MAX_CHUNK_CHARS,
        "note": "If total_chars > chunk_size, use ?chunk=1&size=1800 to read in parts.",
        "content": content
    })


@file_bp.route('/file/sync_data', methods=['GET'])
@file_bp.route('/file/write', methods=['GET'])
def file_sync_data():
    r"""
    Stream chunks to a file.
    GET /file/sync_data?loc=D:\file.md&payload=...&method=init_sync|add_chunk&finalize=false|true
    """
    raw_path, payload, sync_method, finalize = _get_sync_params()

    if not raw_path:
        return jsonify({"status": "error", "error": "Missing 'loc' parameter."}), 400

    if sync_method is None:
        return jsonify({"status": "error", "error": "Invalid method"}), 400

    p, err = _safe_path(raw_path)
    if err:
        return jsonify({"status": "error", "error": err}), 400

    try:
        p.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return jsonify({"status": "error", "error": f"Dir error: {e}"}), 500

    try:
        if sync_method == 'init_sync':
            p.write_text(payload, encoding='utf-8')
        else:
            with open(p, 'a', encoding='utf-8') as f:
                f.write(payload)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "loc": str(p),
        "method": sync_method,
        "finalized": finalize,
        "message": "Sync complete." if finalize else "Chunk synced."
    })


@file_bp.route('/file/edit', methods=['GET'])
def file_edit():
    raw_path = _get_loc()
    if not raw_path:
        return jsonify({"status": "error", "error": "Missing 'loc' parameter."}), 400

    mode = (request.args.get('mode') or '').strip().lower()
    if mode not in ('replace_text', 'edit_lines'):
        return jsonify({
            "status": "error",
            "error": "mode must be 'replace_text' or 'edit_lines'",
        }), 400

    p, err = _safe_path(raw_path)
    if err:
        return jsonify({"status": "error", "error": err}), 400

    chunk_type = request.args.get('chunk_type')
    edit_id = request.args.get('edit_id')
    if chunk_type or edit_id:
        return _handle_edit_stream(p, raw_path, mode)

    return _handle_edit_fast_path(p, raw_path, mode)


@file_bp.route('/file/list', methods=['GET'])
def file_list():
    r"""
    List files and directories inside a folder.
    GET /file/list?loc=D:\project\docs
    Optional: ?ext=.md  — filter by extension
    """
    raw_path = _get_loc()
    ext_filter = request.args.get('ext', '').strip().lower()

    if not raw_path:
        return jsonify({"status": "error", "error": "Missing 'loc' parameter."}), 400

    p, err = _safe_path(raw_path)
    if err:
        return jsonify({"status": "error", "error": err}), 400

    if not p.exists():
        return jsonify({"status": "error", "error": f"Path not found: {raw_path}"}), 404

    if not p.is_dir():
        return jsonify({"status": "error", "error": "Path is a file, not a directory."}), 400

    try:
        items = []
        for entry in sorted(p.iterdir()):
            if ext_filter and entry.is_file() and entry.suffix.lower() != ext_filter:
                continue
            items.append({
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "size_bytes": entry.stat().st_size if entry.is_file() else None,
                "extension": entry.suffix.lower() if entry.is_file() else None
            })
        return jsonify({
            "status": "ok",
            "loc": str(p),
            "count": len(items),
            "items": items
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
