import psycopg2

def conn_db():
    return psycopg2.connect(
        host="localhost",
        database="api_rest",
        user="thiaate",
        password="real"
    )