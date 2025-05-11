from functools import wraps
from flask import request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from conn import conn_db

def check_active_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        
        current_user = get_jwt_identity()
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        
        conn = conn_db()
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT id FROM active_sessions 
                WHERE user_id = %s AND role = %s AND token = %s AND expires_at > NOW()
            """, (current_user['id'], current_user['role'], token))
            
            if cur.fetchone() is None:
                return jsonify({'message': 'Token invalide ou session expirée', 'error': 'invalid_token'}), 401
                
            return fn(*args, **kwargs)
        finally:
            cur.close()
            conn.close()
            
    return wrapper