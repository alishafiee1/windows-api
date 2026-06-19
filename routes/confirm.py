from flask import Blueprint, request, jsonify, render_template
from core.token_store import get_token, approve_token, reject_token, delete_token
from core.runner import run_command

confirm_bp = Blueprint('confirm', __name__)


@confirm_bp.route('/confirm/<token>', methods=['GET'])
def confirm_page(token):
    entry = get_token(token)

    if not entry:
        return render_template('confirm.html',
            state   = "expired",
            token   = token,
            cmd     = None,
            output  = None,
            error   = None
        )

    if entry["status"] == "approved":
        return render_template('confirm.html',
            state   = "already_approved",
            token   = token,
            cmd     = entry["cmd"],
            output  = None,
            error   = None
        )

    if entry["status"] == "rejected":
        return render_template('confirm.html',
            state   = "already_rejected",
            token   = token,
            cmd     = entry["cmd"],
            output  = None,
            error   = None
        )

    return render_template('confirm.html',
        state   = "pending",
        token   = token,
        cmd     = entry["cmd"],
        output  = None,
        error   = None
    )


@confirm_bp.route('/confirm/<token>', methods=['POST'])
def confirm_action(token):
    action = request.form.get('action', '').strip()

    if action not in ('approve', 'reject'):
        return render_template('confirm.html',
            state   = "error",
            token   = token,
            cmd     = None,
            output  = None,
            error   = "Invalid action. Must be 'approve' or 'reject'."
        )

    entry = get_token(token)
    if not entry:
        return render_template('confirm.html',
            state   = "expired",
            token   = token,
            cmd     = None,
            output  = None,
            error   = None
        )

    if action == 'reject':
        reject_token(token)
        delete_token(token)
        return render_template('confirm.html',
            state   = "rejected",
            token   = token,
            cmd     = entry["cmd"],
            output  = None,
            error   = None
        )

    # action == 'approve'
    cmd = approve_token(token)
    result = run_command(cmd)
    delete_token(token)

    return render_template('confirm.html',
        state   = "executed",
        token   = token,
        cmd     = cmd,
        output  = result.get("output"),
        error   = result.get("error")
    )