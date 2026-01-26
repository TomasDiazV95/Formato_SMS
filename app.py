# app.py
from flask import Flask

from routes.sms import sms_bp
from routes.ivr import ivr_bp
from routes.gm import gm_bp

def create_app():
    app = Flask(__name__)
    app.secret_key = "123456"

    app.register_blueprint(sms_bp)
    app.register_blueprint(ivr_bp)
    app.register_blueprint(gm_bp)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5013)
