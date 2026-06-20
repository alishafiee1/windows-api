from pathlib import Path
from urllib.parse import quote

from flask import Blueprint, jsonify, request
from routes.file import MAX_CHUNK_CHARS

help_bp = Blueprint('help', __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INTEGRATION_GUIDE_REL = "docs/perplexity-guid.md"
INTEGRATION_GUIDE_ABS = str(PROJECT_ROOT / INTEGRATION_GUIDE_REL)


@help_bp.route('/help', methods=['GET'])
def show_help():
    base_url = request.host_url.rstrip('/')
    guide_read_url = f"{base_url}/file/read?loc={quote(INTEGRATION_GUIDE_ABS, safe='')}"

    return jsonify({
        "service": "windows-local-integration-api",
        "version": "1.1.0",
        "base_url": base_url,
        "description": "Local API for system operations, command execution, and file synchronization.",
        "integration_guide_file": {
            "relative_loc": INTEGRATION_GUIDE_REL,
            "absolute_loc": INTEGRATION_GUIDE_ABS,
            "description": "Extended client integration guide (workflows, streaming rules, examples).",
            "read_via": guide_read_url,
            "note": "Load this file after /help for complete file-operation workflows.",
        },
        "endpoints": [
            {
                "path": "/help",
                "method": "GET",
                "description": "Returns this API documentation index.",
            },
            {
                "path": "/run",
                "method": "GET",
                "description": "Execute a system command via query string (Standard Integration Method).",
                "query": {
                    "cmd": "string (required) — URL-encoded command to execute",
                },
                "example": f"{base_url}/run?cmd=Get-Date",
            },
            {
                "path": "/run",
                "method": "POST",
                "description": "Execute a system command via JSON body (Fallback for large payloads).",
                "headers": {"Content-Type": "application/json"},
                "body": {"cmd": "string (required) — the command to execute"},
            },
            {
                "path": "/confirm/<token>",
                "method": "GET",
                "description": "Browser user interface to approve or reject pending operations.",
            },
            {
                "path": "/confirm/<token>",
                "method": "POST",
                "description": "Submit approval. Form field: action = approve | reject",
            },
            {
                "path": "/blocklist",
                "method": "GET",
                "description": "Returns operations that require manual human approval.",
            },
            {
                "path": "/file/read",
                "method": "GET",
                "description": "Read a local text file.",
                "query": {
                    "loc": "string (required) — absolute path, e.g. D:\\project\\file.md",
                    "chunk": "int (optional) — 1-based chunk index for pagination",
                    "size": f"int (optional) — chars per chunk, default {MAX_CHUNK_CHARS}",
                },
                "legacy_aliases": {"path": "alias for loc"},
            },
            {
                "path": "/file/sync_data",
                "method": "GET",
                "description": "Stream data chunks to a local destination.",
                "query": {
                    "loc": "string (required) — absolute destination, e.g. D:\\file.md",
                    "payload": "string (required) — URL-encoded data chunk",
                    "method": "'init_sync' (clears destination) or 'add_chunk' (appends)",
                    "finalize": "'true' on the last chunk",
                },
                "legacy_aliases": {
                    "route": "/file/write",
                    "path": "alias for loc",
                    "content": "alias for payload",
                    "mode": "overwrite→init_sync, append→add_chunk",
                    "done": "alias for finalize",
                },
                "streaming_workflow": [
                    "1. First chunk: method=init_sync",
                    "2. Middle chunks: method=add_chunk",
                    f"3. Keep each payload under {MAX_CHUNK_CHARS} characters",
                    "4. Last chunk: method=add_chunk&finalize=true",
                ],
            },
            {
                "path": "/file/list",
                "method": "GET",
                "description": "List files and directories.",
                "query": {
                    "loc": "string (required) — absolute directory path",
                    "ext": "string (optional) — filter by extension, e.g. .md",
                },
                "legacy_aliases": {"path": "alias for loc"},
            },
            {
                "path": "/file/edit",
                "method": "GET",
                "description": "Apply a partial update to an existing text file.",
                "query": {
                    "loc": "string (required)",
                    "mode": "replace_text | edit_lines",
                    "old_text": "fast path — required for replace_text",
                    "new_text": "fast path — required for replace_text; optional for edit_lines",
                    "start_line": "fast path / edit_lines — 1-indexed",
                    "end_line": "fast path / edit_lines — 1-indexed, inclusive",
                    "edit_id": "streaming — session ID (optional on first chunk)",
                    "chunk_type": "streaming — old_text | new_text",
                    "payload": "streaming — URL-encoded text chunk",
                    "init_chunk": "streaming — true clears buffer for chunk_type",
                    "finalize": "streaming — true completes phase or applies edit",
                },
                "modes": {
                    "replace_text": "Exact string match; fails if old_text appears more than once.",
                    "edit_lines": "Replace lines start_line..end_line with new_text; empty new_text deletes.",
                },
                "streaming_workflow": [
                    "replace_text: stream old_text chunks (finalize=true), then new_text chunks (finalize=true applies)",
                    "edit_lines: stream new_text chunks with start_line/end_line; finalize=true applies",
                    f"Keep each payload under {MAX_CHUNK_CHARS} characters",
                ],
                "legacy_aliases": {"path": "alias for loc"},
            },
        ],
        "client_integration_guidelines": {
            "preferred_methods": "GET is preferred for /run. POST is fallback for payload > 2000 chars.",
            "encoding": "Always URL-encode query values (spaces -> %20, backslashes -> %5C).",
            "file_operations": "Prefer /file/* endpoints over system commands for reliability and UTF-8 compliance.",
            "integration_guide": (
                f"See integration_guide_file ({INTEGRATION_GUIDE_REL}) via GET /file/read for "
                "streaming edit rules and full workflow examples."
            ),
            "partial_edits": (
                "Use GET /file/edit for targeted changes; prefer replace_text over edit_lines when possible. "
                "Stream large old_text/new_text via edit_id and chunk_type."
            ),
            "response_handling": (
                "Parse 'status' field ('ok', 'error', 'pending', 'timeout'). "
                "'pending' requires human approval via confirm_url."
            ),
        },
        "response_formats": {
            "ok": {"status": "ok", "output": "stdout (string)", "exit_code": 0},
            "error": {"status": "error", "error": "description of failure"},
            "pending": {
                "status": "pending",
                "confirm_url": f"{base_url}/confirm/abc12345",
                "message": "Requires manual approval.",
            },
            "timeout": {"status": "timeout", "error": "Execution exceeded limits."},
        },
        "operational_notes": [
            "Only accessible from 127.0.0.1 — not exposed to the network.",
            "Commands run in PowerShell (-NoProfile -NonInteractive).",
            "Output truncated at 20000 characters. Default timeout: 30 seconds.",
        ],
    })
