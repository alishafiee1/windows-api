from flask import Blueprint, jsonify, request
from routes.file import MAX_CHUNK_CHARS

help_bp = Blueprint('help', __name__)


@help_bp.route('/help', methods=['GET'])
def show_help():
    base_url = request.host_url.rstrip('/')

    return jsonify({
        "service": "windows-local-integration-api",
        "version": "1.1.0",
        "base_url": base_url,
        "description": "Local API for system operations, command execution, and file synchronization.",
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
        ],
        "client_integration_guidelines": {
            "preferred_methods": "GET is preferred for /run. POST is fallback for payload > 2000 chars.",
            "encoding": "Always URL-encode query values (spaces -> %20, backslashes -> %5C).",
            "file_operations": "Prefer /file/* endpoints over system commands for reliability and UTF-8 compliance.",
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
