import sqlite3
import os

DATABASE = "database/it_helpdesk.db"


def get_db_connection():
    os.makedirs("database", exist_ok=True)

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn