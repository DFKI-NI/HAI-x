import os
import secrets

from flask import Flask, session
from flask_debugtoolbar import DebugToolbarExtension
from dashboard import dash_init

def init_app():
    """Construct core Flask application with embedded Dash app."""
    server = Flask(__name__, instance_relative_config=False)

    # General Config
    FLASK_APP = "main.py"
    server.secret_key = secrets.token_hex(16)

    with server.app_context(), server.test_request_context():
        import routes.routes
        server = dash_init(server)
        return server

app = init_app()
toolbar = DebugToolbarExtension(app)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, ssl_context=('cert.pem', 'key.pem'))

    # app.run_server(host="0.0.0.0", port=5000, ssl_context=('cert.pem', 'key.pem'))
