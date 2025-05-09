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

    keywords = data.get('keywords', '')
    
    conn = conn_db()
    cur = conn.cursor()
    try:
        user_id=user['id']
        cur.execute("""
                INSERT INTO prompts (titre, description, id_user, etat, prix, keywords, created, updated) 
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW()) RETURNING id
            """, (titre, desc, user_id, 'en attente', 1000, keywords))
            
        prompt_id = cur.fetchone()[0]
        conn.commit()
        return jsonify({'msg': 'Prompt soumis avec succès', 'prompt_id': prompt_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@prompt_bp.route('/prompts/<int:prompt_id>/validate', methods=['POST'])
@jwt_required()
def validate_prompt(id_prompt):
    user = get_jwt_identity()
    if user['role'] != 'admin':
        return jsonify({'msg': 'Accès interdit'}), 403

    conn = conn_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE prompts SET etat = 'activer', updated = NOW() WHERE id = %s", (id_prompt,))
        conn.commit()
        return jsonify({'msg': 'Prompt validé'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()
    
@prompt_bp.route('/prompts/<int:prompt_id>/review', methods=['POST'])
@jwt_required()
def request_review(prompt_id):
    user = get_jwt_identity()
    if user['role'] != 'admin':
        return jsonify({'msg': 'Accès interdit'}), 403
    
    data = request.get_json()
    comment = data.get('comment', '')

    conn = conn_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE prompts SET etat = 'à revoir', updated = NOW(), comment = %s 
            WHERE id = %s
        """, (comment, prompt_id))
        conn.commit()
        return jsonify({'msg': 'Prompt envoyé pour révision'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()
@prompt_bp.route('/prompts/<int:prompt_id>/delete', methods=['POST'])
@jwt_required()
def request_delete(prompt_id):
    user = get_jwt_identity()
    
    conn = conn_db()
    cur = conn.cursor()
    
    try:
        # Vérifier si l'utilisateur est le propriétaire du prompt
        cur.execute("SELECT id_user FROM prompts WHERE id = %s", (prompt_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'msg': 'Prompt non trouvé'}), 404
            
        owner_id = result[0]
        
        # Si l'utilisateur est un admin, suppression directe
        if user['role'] == 'admin':
            cur.execute("DELETE FROM prompts WHERE id = %s", (prompt_id,))
            conn.commit()
            return jsonify({'msg': 'Prompt supprimé définitivement'})
        
        # Si l'utilisateur est le propriétaire, marquer pour suppression
        if user['id'] == owner_id:
            cur.execute("""
                UPDATE prompts SET etat = 'à supprimer', updated = NOW() 
                WHERE id = %s
            """, (prompt_id,))
            conn.commit()
            return jsonify({'msg': 'Demande de suppression du prompt envoyée'})
        
        return jsonify({'msg': 'Non autorisé à supprimer ce prompt'}), 403
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@prompt_bp.route('/prompts', methods=['GET'])
def get_prompts():
    search = request.args.get('search', '')
    keyword = request.args.get('keyword', '')
    etat = request.args.get('etat', 'activer')
    
    conn = conn_db()
    cur = conn.cursor()
    query = """
        SELECT id, titre, description, prix, etat, keywords, created 
        FROM prompts 
        WHERE etat = %s
    """
    params = [etat]
    
    # Ajouter la recherche si demandée
    if search:
        query += " AND (titre ILIKE %s OR description ILIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    # Ajouter le filtrage par mot-clé si demandé
    if keyword:
        query += " AND keywords ILIKE %s"
        params.append(f'%{keyword}%')
    
    query += " ORDER BY created DESC"
    
    try:
        cur.execute(query, params)
        prompts = cur.fetchall()
        
        return jsonify([{
            'id': p[0], 
            'titre': p[1], 
            'description': p[2], 
            'prix': p[3], 
            'etat': p[4],
            'keywords': p[5],
            'created': p[6].strftime('%Y-%m-%d %H:%M:%S') if p[6] else None
        } for p in prompts])
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()


@prompt_bp.route('/admin/prompts', methods=['GET'])
@jwt_required()
def get_admin_prompts():
    user = get_jwt_identity()
    if user['role'] != 'admin':
        return jsonify({'msg': 'Accès interdit'}), 403
    
    # Filtrage optionnel par état
    etat = request.args.get('etat', '')
    
    conn = conn_db()
    cur = conn.cursor()
    
    try:
        if etat:
            cur.execute("""
                SELECT p.id, p.titre, p.description, p.prix, p.etat, p.keywords, p.created, u.nom
                FROM prompts p
                JOIN users u ON p.id_user = u.id
                WHERE p.etat = %s
                ORDER BY p.created DESC
            """, (etat,))
        else:
            cur.execute("""
                SELECT p.id, p.titre, p.description, p.prix, p.etat, p.keywords, p.created, u.nom
                FROM prompts p
                JOIN users u ON p.id_user = u.id
                ORDER BY p.created DESC
            """)
        
        prompts = cur.fetchall()
        
        return jsonify([{
            'id': p[0], 
            'titre': p[1], 
            'description': p[2], 
            'prix': p[3], 
            'etat': p[4],
            'keywords': p[5],
            'created': p[6].strftime('%Y-%m-%d %H:%M:%S') if p[6] else None,
            'auteur': p[7]
        } for p in prompts])
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@prompt_bp.route('/prompts/<int:prompt_id>', methods=['GET'])
def get_prompt_detail(prompt_id):
    conn = conn_db()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT p.id, p.titre, p.description, p.prix, p.etat, p.keywords, p.created, u.nom
            FROM prompts p
            JOIN users u ON p.id_user = u.id
            WHERE p.id = %s
        """, (prompt_id,))
        
        p = cur.fetchone()
        
        if not p:
            return jsonify({'msg': 'Prompt non trouvé'}), 404
        
        
        cur.execute("SELECT AVG(score) FROM notes WHERE id_prompt = %s", (prompt_id,))
        avg_score = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM votes WHERE id_prompt = %s", (prompt_id,))
        vote_count = cur.fetchone()[0]
        
        return jsonify({
            'id': p[0], 
            'titre': p[1], 
            'description': p[2], 
            'prix': p[3], 
            'etat': p[4],
            'keywords': p[5],
            'created': p[6].strftime('%Y-%m-%d %H:%M:%S') if p[6] else None,
            'auteur': p[7],
            'note_moyenne': float(avg_score) if avg_score else 0,
            'nombre_votes': vote_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()
       
@prompt_bp.route('/prompts/<int:prompt_id>/vote', methods=['POST'])
@jwt_required()
def vote_prompt(prompt_id):
    user = get_jwt_identity()
    conn = conn_db()
    cur = conn.cursor()

    try:
       
        cur.execute("SELECT id_user, etat FROM prompts WHERE id = %s", (prompt_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'msg': 'Prompt non trouvé'}), 404
            
        owner_id, etat = result
        
        if etat != 'rappel':
            return jsonify({'msg': 'Ce prompt n\'est pas en état de rappel et ne peut pas être voté'}), 400

        
        voter_id = user['id']
        if voter_id == owner_id:
            return jsonify({'msg': 'Impossible de voter pour votre propre prompt'}), 403

        
        cur.execute("SELECT id FROM votes WHERE id_user = %s AND id_prompt = %s", (voter_id, prompt_id))
        if cur.fetchone():
            return jsonify({'msg': 'Vous avez déjà voté pour ce prompt'}), 400

        # Déterminer le poids du vote
        is_same = verif_group(voter_id, owner_id, conn)
        point = 2 if is_same else 1

        # Enregistrer le vote
        cur.execute("INSERT INTO votes (id_user, id_prompt, point) VALUES (%s, %s, %s)",
                    (voter_id, prompt_id, point))

        
        cur.execute("SELECT SUM(point) FROM votes WHERE id_prompt = %s", (prompt_id,))
        total = cur.fetchone()[0] or 0
        
        if total >= 6:
            cur.execute("UPDATE prompts SET etat = 'activer', updated = NOW() WHERE id = %s", (prompt_id,))
        
        conn.commit()
        return jsonify({'msg': 'Vote enregistré', 'points_total': total})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cur.close()
        conn.close()

@prompt_bp.route('/prompts/<int:prompt_id>/rate', methods=['POST'])
@jwt_required()
def note_prompt(prompt_id):
    user = get_jwt_identity()
    data = request.get_json()
    
    if 'score' not in data:
        return jsonify({'msg': 'Score requis'}), 400
        
    score = int(data['score'])

    if score < -10 or score > 10:
        return jsonify({'msg': 'Le score doit être entre -10 et 10'}), 400

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

@prompt_bp.route('/prompts/<int:prompt_id>/buy', methods=['POST'])
def buy_prompt(prompt_id):

    conn = conn_db()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT titre, prix FROM prompts WHERE id = %s AND etat = 'activer'", (prompt_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'msg': 'Prompt non disponible à l\'achat'}), 404
        
        titre, prix = result
        
        
        return jsonify({
            'msg': 'Achat simulé avec succès', 
            'titre': titre, 
            'prix': prix,
            'transaction_id': f'TRANS-{prompt_id}-{datetime.now().strftime("%Y%m%d%H%M%S")}'
        })
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
	
