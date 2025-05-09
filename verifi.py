def  verif_group(id_user1,id_user2, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) FROM user_groups g1 JOIN user_groups g2 
        ON g1.id_group =g2.id_group WHERE g1.id_user = %s AND g2.id_user = %s
    """,(id_user1,id_user2))
    result = cur.fetchone()[0]>0
    cur.close()
    return result