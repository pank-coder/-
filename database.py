import sqlite3
from datetime import datetime


def get_db_path(db_path: str = "data/greh_bot.db") -> str:
    """Get database path, handling sqlite:// prefix if present."""
    if db_path.startswith("sqlite:///"):
        return db_path.replace("sqlite:///", "", 1)
    return db_path


def init_db(db_path: str = "data/greh_bot.db"):
    """Инициализация базы данных."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Таблица пользователей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            status_level INTEGER DEFAULT 0,
            stigma_count INTEGER DEFAULT 0,
            ban_until INTEGER DEFAULT NULL,
            is_permanently_banned BOOLEAN DEFAULT 0,
            interaction_count INTEGER DEFAULT 0
        )
    """)

    # Таблица администраторов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY
        )
    """)

    conn.commit()
    conn.close()


def get_user(user_id: int, username: str = None, db_path: str = "data/greh_bot.db") -> dict:
    """Получить информацию о пользователе."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        # Создаем нового пользователя
        cursor.execute(
            "INSERT INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

    conn.close()
    return dict(row) if row else None


def update_interaction(user_id: int, username: str = None, db_path: str = "data/greh_bot.db") -> dict:
    """Обновить счетчик взаимодействий и проверить повышение звания."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Получаем или создаем пользователя
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        cursor.execute(
            "INSERT INTO users (user_id, username, interaction_count) VALUES (?, ?, 1)",
            (user_id, username)
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    else:
        # Увеличиваем счетчик взаимодействий
        new_count = row["interaction_count"] + 1
        cursor.execute(
            "UPDATE users SET interaction_count = ?, username = ? WHERE user_id = ?",
            (new_count, username, user_id)
        )
        conn.commit()

        # Проверяем повышение звания
        old_level = row["status_level"]
        new_level = calculate_status_level(new_count)

        if new_level > old_level:
            cursor.execute(
                "UPDATE users SET status_level = ? WHERE user_id = ?",
                (new_level, user_id)
            )
            conn.commit()
            row = dict(row)
            row["status_level"] = new_level
            row["interaction_count"] = new_count
            row["level_up"] = True
            conn.close()
            return row

        row = dict(row)
        row["interaction_count"] = new_count

    conn.close()
    return dict(row) if row else None


def calculate_status_level(interaction_count: int) -> int:
    """Рассчитать уровень звания по количеству взаимодействий."""
    if interaction_count >= 30:
        return 3
    elif interaction_count >= 15:
        return 2
    elif interaction_count >= 5:
        return 1
    return 0


def get_status_name(level: int) -> str:
    """Получить название звания по уровню."""
    names = {
        0: "Чужой",
        1: "Заметенный",
        2: "Принятый",
        3: "Избранный"
    }
    return names.get(level, "Чужой")


def add_stigma(user_id: int, db_path: str = "data/greh_bot.db") -> tuple:
    """Добавить клеймо пользователю. Возвращает (stigma_count, ban_type)."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return (0, None)

    stigma_count = row["stigma_count"]
    is_permanently_banned = row["is_permanently_banned"]
    ban_until = row["ban_until"]

    # Если уже перманентно забанен
    if is_permanently_banned:
        conn.close()
        return (stigma_count, "permanent")

    # Проверяем, был ли временный бан и истек ли он
    if ban_until is not None:
        current_time = int(datetime.now().timestamp())
        if current_time >= ban_until:
            # Бан истек, обнуляем клейма
            cursor.execute(
                "UPDATE users SET stigma_count = 0, ban_until = NULL WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            stigma_count = 0
            # Теперь любое новое клеймо после отбытия бана = перманентный бан
            cursor.execute(
                "UPDATE users SET is_permanently_banned = 1 WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            conn.close()
            return (0, "permanent")

    # Добавляем клеймо
    new_stigma = stigma_count + 1
    ban_type = None

    if new_stigma >= 3:
        # Временный бан на 24 часа
        ban_until = int(datetime.now().timestamp()) + 24 * 60 * 60
        cursor.execute(
            "UPDATE users SET stigma_count = ?, ban_until = ? WHERE user_id = ?",
            (new_stigma, ban_until, user_id)
        )
        ban_type = "temporary"
    else:
        cursor.execute(
            "UPDATE users SET stigma_count = ? WHERE user_id = ?",
            (new_stigma, user_id)
        )

    conn.commit()
    conn.close()
    return (new_stigma, ban_type)


def check_ban(user_id: int, db_path: str = "data/greh_bot.db") -> tuple:
    """Проверить, забанен ли пользователь. Возвращает (is_banned, ban_type)."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return (False, None)

    if row["is_permanently_banned"]:
        return (True, "permanent")

    if row["ban_until"] is not None:
        current_time = int(datetime.now().timestamp())
        if current_time < row["ban_until"]:
            return (True, "temporary")
        else:
            # Бан истек, обнуляем
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET stigma_count = 0, ban_until = NULL WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            conn.close()

    return (False, None)


def is_admin(user_id: int, db_path: str = "data/greh_bot.db") -> bool:
    """Проверить, является ли пользователь администратором."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_admin(user_id: int, db_path: str = "data/greh_bot.db"):
    """Добавить администратора."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO admins (user_id) VALUES (?)",
        (user_id,)
    )
    conn.commit()
    conn.close()


def get_user_by_username(username: str, db_path: str = "data/greh_bot.db") -> dict:
    """Получить пользователя по username."""
    db_path = get_db_path(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Убираем @ если есть
    if username.startswith("@"):
        username = username[1:]

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None
