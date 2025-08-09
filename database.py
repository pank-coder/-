import sqlite3
from typing import Optional, List

def init_db():
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance INTEGER DEFAULT 0
    )""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bankers (
        user_id INTEGER PRIMARY KEY
    )""")
    conn.commit()
    conn.close()

def get_balance(user_id: int) -> Optional[int]:
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def update_balance(user_id: int, amount: int):
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)
    """, (user_id,))
    cursor.execute("""
    UPDATE users SET balance = balance + ? WHERE user_id = ?
    """, (amount, user_id))
    conn.commit()
    conn.close()

def is_banker(user_id: int) -> bool:
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM bankers WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return bool(result)

# Добавленные функции для банкиров
def add_banker(user_id: int):
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO bankers (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def remove_banker(user_id: int):
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bankers WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_bankers() -> List[int]:
    conn = sqlite3.connect("pokedb.sqlite")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM bankers")
    bankers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return bankers