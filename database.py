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
            tool_type TEXT NOT NULL DEFAULT 'plagiarism',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Migration: add tool_type to a stored_codes table that already
    # existed before this column was introduced, so old databases
    # (and old rows) don't break.
    cursor.execute("PRAGMA table_info(stored_codes)")
    existing_columns = [row["name"] for row in cursor.fetchall()]
    if "tool_type" not in existing_columns:
        cursor.execute(
            "ALTER TABLE stored_codes ADD COLUMN tool_type TEXT NOT NULL DEFAULT 'plagiarism'"
        )

    conn.commit()
    conn.close()