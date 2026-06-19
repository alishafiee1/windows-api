from flask import Blueprint, request, jsonify
from pathlib import Path

file_bp = Blueprint('file', __name__)

MAX_CHUNK_CHARS = 1800  # safe limit for GET chunk size
MAX_READ_SIZE = 2 * 1024 * 1024  # 2MB


def _get_loc():
    return (request.args.get('loc') or request.args.get('path') or '').strip()


def _safe_path(raw: str):
    """Validate and return a Path. Only absolute Windows paths allowed."""
    p = Path(raw)
    if not p.is_absolute():
        return None, "Only absolute paths are allowed (e.g. D:\\project\\file.md)"
    return p, None


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

    if not p.exists():
        return jsonify({"status": "error", "error": f"File not found: {raw_path}"}), 404

    if not p.is_file():
        return jsonify({"status": "error", "error": "Path is a directory, not a file."}), 400

    file_size = p.stat().st_size
    if file_size > MAX_READ_SIZE:
        return jsonify({
            "status": "error",
            "error": f"File too large ({file_size} bytes). Max allowed: {MAX_READ_SIZE} bytes."
        }), 413

    try:
        content = p.read_text(encoding='utf-8-sig')
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

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
