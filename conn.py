import psycopg2
import os

def conn_db():
    host = os.environ.get('DB_HOST', 'localhost')
    database = os.environ.get('DB_NAME', 'api_rest')
    user = os.environ.get('DB_USER', 'thiaate')
    password = os.environ.get('DB_PASSWORD', 'real')
    
    return psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password
    )