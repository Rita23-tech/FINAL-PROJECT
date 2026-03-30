import sqlite3

DATABASE_NAME = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Users table — added created_at
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stored codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stored_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_text TEXT NOT NULL,
            user_id INTEGER,
            similarity REAL,
            language TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()