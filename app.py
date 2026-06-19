from flask import Flask, redirect
from config import PORT
from routes.help import help_bp
from routes.run import run_bp
from routes.confirm import confirm_bp
from routes.blocklist_route import blocklist_bp
from routes.file import file_bp

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False
app.json.ensure_ascii = False

app.register_blueprint(help_bp)
app.register_blueprint(run_bp)
app.register_blueprint(confirm_bp)
app.register_blueprint(blocklist_bp)
app.register_blueprint(file_bp)


@app.route('/')
def index():
    return redirect('/help')


@app.before_request
def restrict_to_localhost():
    from flask import request, abort
    if request.remote_addr not in ('127.0.0.1', '::1'):
        abort(403)


if __name__ == '__main__':
    from core.server_lifecycle import prepare_server_start, register_server_shutdown

    stopped_process_ids = prepare_server_start(PORT)
    register_server_shutdown()

    if stopped_process_ids:
        print(f"* Stopped previous server process(es): {', '.join(map(str, stopped_process_ids))}")

    print(f"* windows-cmd-api running on http://127.0.0.1:{PORT}")
    print(f"* Open http://127.0.0.1:{PORT}/help for usage guide")

    try:
        app.run(host='127.0.0.1', port=PORT, debug=False, use_reloader=False)
    finally:
        from core.server_lifecycle import remove_stored_process_id
        remove_stored_process_id()