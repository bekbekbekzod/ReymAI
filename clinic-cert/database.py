import sqlite3
import os
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance", "clinic.db")


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uuid TEXT UNIQUE NOT NULL,
            code_hash TEXT NOT NULL,
            full_name TEXT,
            birth_date TEXT,
            passport TEXT,
            address TEXT,
            diagnosis TEXT,
            purpose TEXT,
            doctor_name TEXT,
            clinic_name TEXT,
            issue_date TEXT,
            valid_until TEXT,
            pdf_filename TEXT,
            created_at TEXT,
            created_by TEXT
        );

        CREATE TABLE IF NOT EXISTS verify_attempts (
            uuid TEXT PRIMARY KEY,
            fail_count INTEGER DEFAULT 0,
            locked_until TEXT
        );
        """
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Baza yaratildi:", DB_PATH)
