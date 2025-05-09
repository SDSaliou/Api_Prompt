from flask import Flask
from flask_jwt_extended import JWTManager
from auth import auth
from prompt import prompt_bp

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'real'
jwt = JWTManager(app)


app.register_blueprint(auth)
app.register_blueprint(prompt_bp)

if __name__ == '__main__':
    app.run(debug=True)  