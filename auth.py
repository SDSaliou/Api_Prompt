from flask import Blueprint,request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from conn import conn_db

auth = Blueprint('auth', __name__)

@auth.route('inscription', methods=['POST'])
def inscription():
    data = request.get_json()
    user_name = data['nom']
    role = data.get('role','user')
    password = data['password']
    email = data['email']

    con = conn_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (nom, email, password, role) VALUES (%s,%s,%s,%s)", (user_name,email,password,role)
        )
        con.commit()
        return jsonify({'message': 'User created successfully'}), 201
    except Exception as e:
        return jsonify({'message':'Error','error':str(e)}), 400
    finally:
        cur.close()
        con.close()

@auth.route('login', methods=['POST'])
def login():
    data = request.get_json()
    email = data['email']
    password = data['password']

    con = conn_db()
    cur = con.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    con.close()

    if user and user[3] == password:
        token = create_access_token(identity={'email':email, 'role': user[0]})
        return jsonify({'token': token}), 200
    return jsonify({'message': 'Invalid'}), 401

@auth.route('/admin', methods=['GET'])
@jwt_required()
def admin():
    current_user = get_jwt_identity()
    if current_user['role']!='admin':
        return jsonify({'message': 'Access refus'}), 403
    return jsonify({'message': 'Acces accepté'})

