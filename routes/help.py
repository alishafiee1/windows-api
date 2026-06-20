from pathlib import Path

from flask import Blueprint, Response, request
from routes.file import MAX_CHUNK_CHARS

help_bp = Blueprint('help', __name__)

GUIDE_PATH = Path(__file__).resolve().parent.parent / "docs" / "perplexity-guid.md"


@help_bp.route('/help', methods=['GET'])
def show_help():
    text = GUIDE_PATH.read_text(encoding='utf-8')
    text = text.replace('{{base_url}}', request.host_url.rstrip('/'))
    text = text.replace('{{max_chunk_chars}}', str(MAX_CHUNK_CHARS))
    return Response(text, mimetype='text/markdown; charset=utf-8')
