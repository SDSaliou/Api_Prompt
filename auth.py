from flask import Blueprint, request, jsonify
#from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity,decode_token
from conn import conn_db
import bcrypt
import jwt
from datetime import datetime, timedelta
import os
from middleware import token_required, create_token


auth = Blueprint('auth', __name__)

@auth.route('/inscription', methods=['POST'])
@token_required
def inscription(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé : seul un admin peut créer des utilisateurs'}), 403

    data = request.get_json()
    user_name = data.get('nom')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'user')

    if not user_name or not email or not password:
        return jsonify({'message': 'Champs manquants'}), 400

    if role not in ['admin', 'user']:
        return jsonify({'message': 'Rôle invalide'}), 400

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    con = conn_db()
    cur = con.cursor()

    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return jsonify({'message': 'Email déjà utilisé'}), 409

        cur.execute("INSERT INTO users (nom, email, password, role) VALUES (%s, %s, %s, %s)",
                    (user_name, email, hashed_password, role))
        con.commit()

        return jsonify({'message': f"Utilisateur {user_name} créé avec succès"}), 201

    except Exception as e:
        con.rollback()
        return jsonify({'message': 'Erreur', 'error': str(e)}), 500

    finally:
        cur.close()
        con.close()
@auth.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']

    con = conn_db()
    cur = con.cursor()
    cur.execute("SELECT id, nom, email, password, role FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    con.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
        token = create_token(user[0], user[1], user[2], user[4])
        return jsonify({'token': token}), 200
    
    return jsonify({'message': 'Email ou mot de passe invalide'}), 401

@auth.route('/admin', methods=['GET'])
@token_required
def admin(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403

    return jsonify({'message': 'Accès accepté'})

@auth.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403
    
    con = conn_db()
    cur = con.cursor()
    cur.execute("SELECT id, nom, email, role FROM users")
    users = cur.fetchall()
    cur.close()
    con.close()
    
    return jsonify([{
        'id': u[0], 'nom': u[1], 'email': u[2], 'role': u[3]
    } for u in users]), 200

@auth.route('/create-group', methods=['POST'])
@token_required
def create_group(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403
    
    data = request.get_json()
    nom_group = data['nom_group']
    user_ids = data.get('user_ids', [])
    
    con = conn_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO groups (nom_group) VALUES (%s) RETURNING id", (nom_group,))
        group_id = cur.fetchone()[0]
        
        for user_id in user_ids:
            cur.execute("INSERT INTO user_groups (id_user, id_group) VALUES (%s, %s)", 
                       (user_id, group_id))
        
        con.commit()
        return jsonify({'message': 'Groupe créé avec succès', 'id_group': group_id}), 201
    except Exception as e:
        con.rollback()
        return jsonify({'message': 'Erreur', 'error': str(e)}), 400
    finally:
        cur.close()
        con.close()

@auth.route('/add-group', methods=['POST'])
@token_required
def add_user_to_group(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403
    
    data = request.get_json()
    user_id = data['id_user']
    group_id = data['id_group']
    
    con = conn_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO user_groups (id_user, id_group) VALUES (%s, %s)", 
                   (user_id, group_id))
        con.commit()
        return jsonify({'message': 'Utilisateur ajouté au groupe avec succès'}), 201
    except Exception as e:
        return jsonify({'message': 'Erreur', 'error': str(e)}), 400
    finally:
        cur.close()
        con.close()

@auth.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    conn = conn_db()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO blacklisted_tokens (token, id_user, blacklisted_on) VALUES (%s, %s, NOW())", 
                   (token, current_user['id']))
        conn.commit()
        return jsonify({'message': 'Déconnexion réussie'}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({'message': 'Erreur lors de la déconnexion', 'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()