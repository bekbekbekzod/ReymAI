"""
Admin foydalanuvchi yaratish uchun skript.
Ishlatish: python3 create_admin.py <username> <password>
"""
import sys
from werkzeug.security import generate_password_hash
from database import get_db, init_db, DB_PATH
import sqlite3

def main():
    if len(sys.argv) != 3:
        print("Ishlatish: python3 create_admin.py <username> <password>")
        sys.exit(1)

    username, password = sys.argv[1], sys.argv[2]
    init_db()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password)),
        )
        conn.commit()
        print(f"Admin '{username}' muvaffaqiyatli yaratildi.")
    except sqlite3.IntegrityError:
        print(f"Xato: '{username}' nomli admin allaqachon mavjud.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
