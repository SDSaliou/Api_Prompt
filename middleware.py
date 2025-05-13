from functools import wraps
from flask import request, jsonify
#from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from conn import conn_db
import jwt
import os
from datetime import datetime, timedelta

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorator(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"message": "Token d'accès requis!"}), 401
        
        token = auth_header.split(' ')[1]
        print("TOKEN REÇU (depuis header):", token)

        try:
            # Décodage du token
            payload = jwt.decode(
                token, 
                os.environ.get('JWT_SECRET_KEY', 'realthiaate'),
                algorithms=['HS256']
            )
            print("Payload décodé:", payload)
            if 'exp' not in payload:
                return jsonify({"message": "Champ 'exp' manquant dans le token!"}), 401

            # Vérifier si le token a expiré
            if datetime.fromtimestamp(payload['exp']) < datetime.utcnow():
                return jsonify({"message": "Token expiré!"}), 401
            
            # Récupérer les informations de l'utilisateur depuis la base de données
            conn = conn_db()
            cur = conn.cursor()
            cur.execute("SELECT id, nom, email, role FROM users WHERE id = %s", (payload['id'],))
            user_data = cur.fetchone()
            cur.close()
            conn.close()
            
            if not user_data:
                return jsonify({"message": "Utilisateur non trouvé!"}), 404
            
            # Créer un objet current_user avec les données de l'utilisateur
            current_user = {
                'id': user_data[0],
                'nom': user_data[1],
                'email': user_data[2],
                'role': user_data[3]
            }
            return f(current_user, *args, **kwargs)
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token expiré!"}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({"message": f"Token invalide: {str(e)}"}), 401
        except Exception as e:
            return jsonify({"message": f"Erreur lors du traitement du token: {str(e)}"}), 500

        return decorator
    
    
    return decorator

# Fonction pour créer un token JWT
def create_token(user_id, nom, email, role):
    expiration = datetime.utcnow() + timedelta(hours=1)
    
    payload = {
        'id': user_id,
        'nom': nom,
        'email': email,
        'role': role,
        'exp': int(expiration.timestamp()) 
    }
    
    print("Payload généré:", payload)

    token = jwt.encode(
        payload,
        os.environ.get('JWT_SECRET_KEY', 'realthiaate'),
        algorithm='HS256'
    )

    print("Token généré:", token)
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return token