from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from conn import conn_db
import bcrypt

auth = Blueprint('auth', __name__)

@auth.route('/inscription', methods=['POST'])
def inscription():
    data = request.get_json()
    user_name = data['nom']
    role = data.get('role', 'user')
    password = data['password']
    email = data['email']
    
    # Vérifier que le rôle est valide
    if role not in ['admin', 'user']:
        return jsonify({'message': 'Rôle invalide'}), 400
    
    # Hasher le mot de passe pour sécurité
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    con = conn_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (nom, email, password, role) VALUES (%s, %s, %s, %s)", 
                   (user_name, email, hashed_password, role))
        con.commit()
        return jsonify({'message': 'Utilisateur créé avec succès'}), 201
    except Exception as e:
        return jsonify({'message': 'Erreur', 'error': str(e)}), 400
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
        token = create_access_token(identity={'id': user[0], 'email': email, 'role': user[4]})
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Email ou mot de passe invalide'}), 401

@auth.route('/admin', methods=['GET'])
@jwt_required()
def admin():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403
    return jsonify({'message': 'Accès accepté'})

@auth.route('/users', methods=['GET'])
@jwt_required()
def get_users():
    current_user = get_jwt_identity()
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
@jwt_required()
def create_group():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403
    
    data = request.get_json()
    nom_group = data['nom']
    user_ids = data.get('user_ids', [])
    
    con = conn_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO groups (nom) VALUES (%s) RETURNING id", (nom_group,))
        group_id = cur.fetchone()[0]
        
        for user_id in user_ids:
            cur.execute("INSERT INTO user_groups (id_user, id_group) VALUES (%s, %s)", 
                       (user_id, group_id))
        
        con.commit()
        return jsonify({'message': 'Groupe créé avec succès', 'group_id': group_id}), 201
    except Exception as e:
        con.rollback()
        return jsonify({'message': 'Erreur', 'error': str(e)}), 400
    finally:
        cur.close()
        con.close()

@auth.route('/add-user-to-group', methods=['POST'])
@jwt_required()
def add_user_to_group():
    current_user = get_jwt_identity()
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Accès refusé'}), 403
    
    data = request.get_json()
    user_id = data['user_id']
    group_id = data['group_id']
    
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