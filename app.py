from flask import Flask,jsonify
from flask_jwt_extended import JWTManager
from auth import auth
from prompt import prompt_bp
from datetime import timedelta

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'realthiaate'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)
jwt = JWTManager(app)

@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({
        'message': 'Le token a expiré',
        'error': 'token_expired'
    }), 401

@jwt.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({
        'message': 'Signature de token invalide',
        'error': 'invalid_token'
    }), 401

@jwt.unauthorized_loader
def missing_token_callback(error):
    return jsonify({
        'message': 'Token d\'accès requis',
        'error': 'authorization_required'
    }), 401

app.register_blueprint(auth, url='api/auth')
app.register_blueprint(prompt_bp, url ='/api')

@app.route('/')
def index():
    return jsonify({
        'message': 'API REST pour la gestion des prompts',
        'status': 'online'
    })


if __name__ == '__main__':
    app.run(debug=True)  