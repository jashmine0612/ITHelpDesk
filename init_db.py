import sqlite3
from database import DATABASE
from werkzeug.security import generate_password_hash


with open("database/schema.sql", "r") as file:
    schema = file.read()

conn = sqlite3.connect(DATABASE)

conn.executescript(schema)


users = [
    ("Jashmine", "jashmine@example.com", "1234", "user"),
    ("Support Staff", "support@example.com", "1234", "support"),
    ("Administrator", "admin@example.com", "1234", "admin")
]

for name, email, password, role in users:

    password_hash = generate_password_hash(password)

    conn.execute("""
        INSERT OR IGNORE INTO users
        (name, email, password_hash, role)
        VALUES (?, ?, ?, ?)
    """, (
        name,
        email,
        password_hash,
        role
    ))


conn.commit()
conn.close()

print("Database initialized successfully.")