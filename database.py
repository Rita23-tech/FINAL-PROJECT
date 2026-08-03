import os
import psycopg2
import psycopg2.extras


def get_db():
    conn = psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=psycopg2.extras.RealDictCursor)
    return conn


def create_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Stored codes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stored_codes (
            id SERIAL PRIMARY KEY,
            code_text TEXT NOT NULL,
            user_id INTEGER REFERENCES users(id),
            similarity REAL,
            language TEXT NOT NULL,
            tool_type TEXT NOT NULL DEFAULT 'plagiarism',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Migration: add tool_type to a stored_codes table that already
    # existed before this column was introduced, so old databases
    # (and old rows) don't break.
    cursor.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'stored_codes'
    """)
    existing_columns = [row["column_name"] for row in cursor.fetchall()]
    if "tool_type" not in existing_columns:
        cursor.execute(
            "ALTER TABLE stored_codes ADD COLUMN tool_type TEXT NOT NULL DEFAULT 'plagiarism'"
        )

    conn.commit()
    conn.close()