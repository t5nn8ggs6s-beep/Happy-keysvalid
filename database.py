import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    key TEXT,
    tariff TEXT,
    expires TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS keys (
    key TEXT PRIMARY KEY,
    used INTEGER DEFAULT 0
)
""")

conn.commit()

# загрузка ключей из файла
def load_keys():
    with open("keys.txt") as f:
        for line in f:
            key = line.strip()
            try:
                cursor.execute("INSERT INTO keys (key) VALUES (?)", (key,))
            except:
                pass
    conn.commit()

def get_key():
    cursor.execute("SELECT key FROM keys WHERE used=0 LIMIT 1")
    row = cursor.fetchone()
    if row:
        key = row[0]
        cursor.execute("UPDATE keys SET used=1 WHERE key=?", (key,))
        conn.commit()
        return key
    return None

def save_user(user_id, key, tariff, days):
    expires = datetime.now() + timedelta(days=days)
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, key, tariff, expires) VALUES (?, ?, ?, ?)",
        (user_id, key, tariff, expires.isoformat())
    )
    conn.commit()

def get_user(user_id):
    cursor.execute("SELECT key, tariff, expires FROM users WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    if row:
        key, tariff, expires = row
        return key, tariff, datetime.fromisoformat(expires)
    return None

def extend_user(user_id, days):
    data = get_user(user_id)
    if data:
        key, tariff, expires = data
        new_expire = max(datetime.now(), expires) + timedelta(days=days)
        cursor.execute("UPDATE users SET expires=? WHERE user_id=?", (new_expire.isoformat(), user_id))
        conn.commit()
        return new_expire
    return None

def all_users():
    cursor.execute("SELECT user_id, key, tariff, expires FROM users")
    return cursor.fetchall()
