from flask import Blueprint, jsonify
from core.blocklist import get_blocklist

blocklist_bp = Blueprint('blocklist', __name__)


@blocklist_bp.route('/blocklist', methods=['GET'])
def blocklist_route():
    rules = get_blocklist()
    return jsonify({
        "count": len(rules),
        "rules": rules
    })