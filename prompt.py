from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from conn import conn_db
from verifi import verif_group
from datetime import datetime, timedelta

prompt_bp = Blueprint('prompt', __name__)

@prompt_bp.route('/prompts', methods=['POST'])
@jwt_required()
def propose_prompt():
    user = get_jwt_identity()
    data = request.get_json()
    titre = data['titre']
    desc = data['description']

    conn = conn_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (user['email'],))
    user_id = cur.fetchone()[0]
    cur.execute("INSERT INTO prompts (titre, description, id_user) VALUES (%s, %s, %s)", (titre, desc, user_id))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'msg': 'Prompt soumis'}), 201

@prompt_bp.route('/prompts/<int:prompt_id>/validate', methods=['POST'])
@jwt_required()
def validate_prompt(id_prompt):
    user = get_jwt_identity()
    if user['role'] != 'admin':
        return jsonify({'msg': 'Accès interdit'}), 403

    conn = conn_db()
    cur = conn.cursor()
    cur.execute("UPDATE prompts SET etat = 'activer', updated = NOW() WHERE id = %s", (id_prompt,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'msg': 'Prompt validé'})

@prompt_bp.route('/prompts', methods=['GET'])
def get_prompts():
    conn = conn_db()
    cur = conn.cursor()
    cur.execute("SELECT id, titre, description, prix, etat FROM prompts WHERE etat = 'activer'")
    prompts = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        'id': p[0], 'titre': p[1], 'description': p[2], 'prix': p[3], 'etat': p[4]
    } for p in prompts])

@prompt_bp.route('/prompts/<int:prompt_id>/vote', methods=['POST'])
@jwt_required()
def vote_prompt(prompt_id):
    user = get_jwt_identity()
    conn = conn_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE email = %s", (user['email'],))
    voter_id = cur.fetchone()[0]
    cur.execute("SELECT id_user FROM prompts WHERE id = %s", (prompt_id,))
    owner_id = cur.fetchone()[0]

    if voter_id == owner_id:
        return jsonify({'msg': 'Impossible de voter pour votre propre prompt'}), 403

    is_same = verif_group(voter_id, owner_id, conn)
    point = 2 if is_same else 1

    try:
        cur.execute("INSERT INTO votes (id_user,id_prompt, point) VALUES (%s, %s, %s)",
                    (voter_id, prompt_id, point))

        cur.execute("SELECT SUM(point) FROM votes WHERE id_prompt = %s", (prompt_id,))
        total = cur.fetchone()[0]
        if total >= 6:
            cur.execute("UPDATE prompts SET etat = 'activer', updated = NOW() WHERE id = %s", (prompt_id,))
        conn.commit()
        return jsonify({'msg': 'Vote enregistré', 'points_total': total})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@prompt_bp.route('/prompts/<int:prompt_id>/rate', methods=['POST'])
@jwt_required()
def note_prompt(prompt_id):
    user = get_jwt_identity()
    score = int(request.json['score'])

    conn = conn_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email = %s", (user['email'],))
    note_id = cur.fetchone()[0]
    cur.execute("SELECT id_user FROM prompts WHERE id = %s", (prompt_id,))
    owner_id = cur.fetchone()[0]

    if note_id == owner_id:
        return jsonify({'msg': 'Vous ne pouvez pas noter votre propre prompt'}), 403

    is_same = verif_group(note_id, owner_id, conn)
    point = 0.6 if is_same else 0.4

    try:
        cur.execute("""
            INSERT INTO notes (id_user, id_prompt, score, point)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, prompt_id) DO UPDATE SET score = EXCLUDED.score, point = EXCLUDED.point
        """, (note_id, prompt_id, score, point))

        cur.execute("""
            SELECT SUM(score * point) / SUM(point)
            FROM notes WHERE id_prompt = %s
        """, (prompt_id,))
        moyenne = cur.fetchone()[0]
        nouveau_prix = int(1000 * (1 + moyenne))

        cur.execute("UPDATE prompts SET prix = %s WHERE id = %s", (nouveau_prix, prompt_id))
        conn.commit()
        return jsonify({'msg': 'Note prise en compte', 'moyenne': moyenne, 'nouveau_prix': nouveau_prix})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@prompt_bp.route('/prompts/auto-update-states', methods=['POST'])
def auto_update_prompt_states():
    conn = conn_db()
    cur = conn.cursor()
    now = datetime.utcnow()

    cur.execute("""
        UPDATE prompts SET etat = 'rappel'
        WHERE etat = 'en attente' AND updated <= %s
    """, (now - timedelta(days=2),))

    cur.execute("""
        UPDATE prompts SET etat = 'rappel'
        WHERE etat = 'à supprimer' AND updated <= %s
    """, (now - timedelta(days=1),))

    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'msg': 'Mise à jour des états automatique effectuée'})
	
