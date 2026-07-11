import sqlite3
import bcrypt

DB_PATH = "auth.db"

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        hashed_password TEXT NOT NULL
    )
""")

username = "admin"
password = "password123"

cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
if not cursor.fetchone():
    hashed_pw = get_password_hash(password)
    cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (username, hashed_pw))
    print(f"Created default user: {username} / {password}")
else:
    print(f"User {username} already exists. Use password: {password} (or your modified password).")

conn.commit()
conn.close()
