from flask import Flask,jsonify, request
#from flask_jwt_extended import JWTManager
from auth import auth
import jwt
from prompt import prompt_bp
from datetime import timedelta, datetime
import os

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY','realthiaate')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

#jwt = JWTManager(app)

# @jwt.expired_token_loader
# def expired_token_callback(jwt_header, jwt_payload):
#     return jsonify({
#         'message': 'Le token a expiré',
#         'error': 'token_expired'
#     }), 401

# @jwt.invalid_token_loader
# def invalid_token_callback(error):
#     return jsonify({
#         'message': 'Signature de token invalide',
#         'error': 'invalid_token'
#     }), 401

# @jwt.unauthorized_loader
# def missing_token_callback(error):
#     return jsonify({
#         'message': 'Token d\'accès requis',
#         'error': 'authorization_required'
#     }), 401

# Middleware pour vérifier les tokens JWT expiré/invalide
@app.errorhandler(401)
def unauthorized_handler(error):
    return jsonify({'message': 'Non autorisé', 'error': 'unauthorized'}), 401

# Fonction pour gérer les tokens JWT
def verify_jwt():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, {'message': 'Token d\'accès requis', 'error': 'authorization_required'}
    
    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        # Vérifier l'expiration
        if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
            return None, {'message': 'Le token a expiré', 'error': 'token_expired'}
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, {'message': 'Le token a expiré', 'error': 'token_expired'}
    except (jwt.InvalidTokenError, jwt.DecodeError):
        return None, {'message': 'Signature de token invalide', 'error': 'invalid_token'}


app.register_blueprint(auth, url_prefix='/api/auth')
app.register_blueprint(prompt_bp, url_prefix ='/api')

@app.route('/')
def index():
    return jsonify({
        'message': 'API REST pour la gestion des prompts',
        'status': 'online'
    })


if __name__ == '__main__':
    app.run(debug=True)  