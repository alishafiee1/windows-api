from flask import Blueprint, request, jsonify
from core.blocklist import is_dangerous
from core.token_store import create_token
from core.runner import run_command
from config import PORT

run_bp = Blueprint('run', __name__)


def _execute_command(cmd: str):
    if not cmd:
        return jsonify({
            "status": "error",
            "error": "'cmd' must not be empty."
        }), 400

    if is_dangerous(cmd):
        token = create_token(cmd)
        confirm_url = f"http://127.0.0.1:{PORT}/confirm/{token}"
        return jsonify({
            "status":      "pending",
            "token":       token,
            "confirm_url": confirm_url,
            "message":     "Command matched a blocklist rule and requires manual approval. Open confirm_url in your browser."
        }), 202

    result = run_command(cmd)

    if result["status"] == "ok":
        return jsonify(result), 200
    elif result["status"] == "timeout":
        return jsonify(result), 408
    else:
        return jsonify(result), 500


def _extract_command_from_request():
    if request.method == 'GET':
        if 'cmd' not in request.args:
            return None, "Query string must include a 'cmd' parameter. Example: /run?cmd=Get-Date"
        return request.args.get('cmd', '').strip(), None

    data = request.get_json(silent=True)
    if not data or 'cmd' not in data:
        return None, "Request body must be JSON with a 'cmd' field."
    return data['cmd'].strip(), None


@run_bp.route('/run', methods=['GET', 'POST'])
def run_route():
    cmd, extract_error = _extract_command_from_request()

    if extract_error:
        return jsonify({
            "status": "error",
            "error": extract_error
        }), 400

    return _execute_command(cmd)
