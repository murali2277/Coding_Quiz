from flask import Flask
from routes.auth import auth_bp
import config

app = Flask(__name__)
app.config.from_object(config)

app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True) 