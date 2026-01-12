import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple

DB_FILE = os.getenv("DATABASE_FILE", "bot_database.db")

def get_connection():
    """Получить соединение с БД"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Инициализация базы данных"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Таблица администраторов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица каналов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица шаблонов подписей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            template_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Таблица связи каналов и шаблонов (один канал - один шаблон)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channel_templates (
            channel_id TEXT PRIMARY KEY,
            template_id INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
            FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
        )
    """)
    
    # Таблица связи админов и каналов (many-to-many)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_channels (
            admin_id INTEGER,
            channel_id TEXT,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (admin_id, channel_id),
            FOREIGN KEY (admin_id) REFERENCES admins(user_id) ON DELETE CASCADE,
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
        )
    """)
    
    # Таблица статистики загрузок (с полями для file_id и message_id)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS upload_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            channel_id TEXT,
            title TEXT,
            season INTEGER,
            episode INTEGER,
            file_id TEXT,
            message_id TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES admins(user_id),
            FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
        )
    """)

    # Миграции для добавления колонок в существующие таблицы (совместимость)
    cursor.execute("PRAGMA table_info(admins)")
    admin_cols = [row['name'] for row in cursor.fetchall()]
    if 'role' not in admin_cols:
        cursor.execute("ALTER TABLE admins ADD COLUMN role TEXT NOT NULL DEFAULT 'junior'")
    if 'name' not in admin_cols:
        cursor.execute("ALTER TABLE admins ADD COLUMN name TEXT")

    cursor.execute("PRAGMA table_info(upload_stats)")
    up_cols = [row['name'] for row in cursor.fetchall()]
    if 'file_id' not in up_cols:
        cursor.execute("ALTER TABLE upload_stats ADD COLUMN file_id TEXT")
    if 'message_id' not in up_cols:
        cursor.execute("ALTER TABLE upload_stats ADD COLUMN message_id TEXT")

    conn.commit()
    conn.close()

def migrate_from_json(json_file: str):
    """Миграция данных из admins.json в БД"""
    if not os.path.exists(json_file):
        return
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        admins = data.get('admins', [])
        for admin_id in admins:
            # Проверяем, есть ли уже в БД
            if not get_admin(admin_id):
                add_admin(admin_id, username=None)
        
        print(f"Migrated {len(admins)} admins from {json_file}")
    except Exception as e:
        print(f"Migration error: {e}")

# ================== ADMIN FUNCTIONS ==================

def add_admin(user_id: int, username: Optional[str] = None, role: str = 'junior', name: Optional[str] = None) -> bool:
    """Добавить администратора (или обновить существующего)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO admins (user_id, username, role, name) VALUES (?, ?, ?, ?)",
            (user_id, username, role, name)
        )
        # Обновляем поля, если админ уже существует (username/role/name)
        cursor.execute(
            "UPDATE admins SET username = COALESCE(?, username), role = COALESCE(?, role), name = COALESCE(?, name) WHERE user_id = ?",
            (username, role, name, user_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding admin: {e}")
        return False

def remove_admin(user_id: int) -> bool:
    """Удалить администратора"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing admin: {e}")
        return False

def get_admin(user_id: int) -> Optional[Dict]:
    """Получить информацию об админе"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_admins() -> List[Dict]:
    """Получить список всех админов"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins ORDER BY added_at")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом"""
    return get_admin(user_id) is not None

def get_admins_by_role(role: str) -> List[Dict]:
    """Получить админов по роли (main/junior)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE role = ? ORDER BY added_at", (role,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def set_admin_role(user_id: int, role: str) -> bool:
    """Установить роль администратора ("main" или "junior")"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE admins SET role = ? WHERE user_id = ?", (role, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting admin role: {e}")
        return False

# ================== CHANNEL FUNCTIONS ==================

def add_channel(channel_id: str, channel_name: str) -> bool:
    """Добавить канал"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO channels (channel_id, channel_name) VALUES (?, ?)",
            (channel_id, channel_name)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error adding channel: {e}")
        return False

def remove_channel(channel_id: str) -> bool:
    """Удалить канал"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing channel: {e}")
        return False

def get_channel(channel_id: str) -> Optional[Dict]:
    """Получить информацию о канале"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_channels() -> List[Dict]:
    """Получить список всех каналов"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels ORDER BY added_at")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ================== ADMIN-CHANNEL ASSIGNMENT ==================

def assign_admin_to_channel(admin_id: int, channel_id: str) -> bool:
    """Назначить админа на канал"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO admin_channels (admin_id, channel_id) VALUES (?, ?)",
            (admin_id, channel_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error assigning admin to channel: {e}")
        return False

def unassign_admin_from_channel(admin_id: int, channel_id: str) -> bool:
    """Убрать админа с канала"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM admin_channels WHERE admin_id = ? AND channel_id = ?",
            (admin_id, channel_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error unassigning admin from channel: {e}")
        return False

def get_admin_channels(admin_id: int) -> List[Dict]:
    """Получить список каналов админа"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.* FROM channels c
        JOIN admin_channels ac ON c.channel_id = ac.channel_id
        WHERE ac.admin_id = ?
        ORDER BY c.channel_name
    """, (admin_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_channel_admins(channel_id: str) -> List[Dict]:
    """Получить список админов канала"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.* FROM admins a
        JOIN admin_channels ac ON a.user_id = ac.admin_id
        WHERE ac.channel_id = ?
        ORDER BY a.username
    """, (channel_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# ================== STATISTICS ==================

def log_upload(admin_id: int, channel_id: str, title: str, season: int, episode: int, file_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
    """Записать загрузку в статистику (с file_id и message_id)"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO upload_stats (admin_id, channel_id, title, season, episode, file_id, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (admin_id, channel_id, title, season, episode, file_id, message_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error logging upload: {e}")
        return False

def get_admin_stats(admin_id: int) -> Dict:
    """Получить статистику админа"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Общее количество загрузок
    cursor.execute(
        "SELECT COUNT(*) as total FROM upload_stats WHERE admin_id = ?",
        (admin_id,)
    )
    total = cursor.fetchone()['total']
    
    # По каналам
    cursor.execute("""
        SELECT c.channel_name, COUNT(*) as count
        FROM upload_stats us
        JOIN channels c ON us.channel_id = c.channel_id
        WHERE us.admin_id = ?
        GROUP BY c.channel_id
        ORDER BY count DESC
    """, (admin_id,))
    by_channel = [dict(row) for row in cursor.fetchall()]
    
    # Последние загрузки
    cursor.execute("""
        SELECT title, season, episode, uploaded_at
        FROM upload_stats
        WHERE admin_id = ?
        ORDER BY uploaded_at DESC
        LIMIT 5
    """, (admin_id,))
    recent = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'total': total,
        'by_channel': by_channel,
        'recent': recent
    }

def get_channel_stats(channel_id: str) -> Dict:
    """Получить статистику канала"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Общее количество загрузок
    cursor.execute(
        "SELECT COUNT(*) as total FROM upload_stats WHERE channel_id = ?",
        (channel_id,)
    )
    total = cursor.fetchone()['total']
    
    # По админам
    cursor.execute("""
        SELECT a.user_id, a.username, COUNT(*) as count
        FROM upload_stats us
        JOIN admins a ON us.admin_id = a.user_id
        WHERE us.channel_id = ?
        GROUP BY a.user_id
        ORDER BY count DESC
    """, (channel_id,))
    by_admin = [dict(row) for row in cursor.fetchall()]
    
    # Последние загрузки
    cursor.execute("""
        SELECT title, season, episode, uploaded_at, admin_id
        FROM upload_stats
        WHERE channel_id = ?
        ORDER BY uploaded_at DESC
        LIMIT 5
    """, (channel_id,))
    recent = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return {
        'total': total,
        'by_admin': by_admin,
        'recent': recent
    }

def get_all_stats() -> List[Dict]:
    """Получить общую статистику всех админов"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            a.user_id,
            a.username,
            COUNT(us.id) as total_uploads,
            MAX(us.uploaded_at) as last_upload
        FROM admins a
        LEFT JOIN upload_stats us ON a.user_id = us.admin_id
        GROUP BY a.user_id
        ORDER BY total_uploads DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# ================== TEMPLATE FUNCTIONS ==================

def add_template(name: str, template_text: str) -> Optional[int]:
    """Добавить шаблон подписи"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO templates (name, template_text) VALUES (?, ?)",
            (name, template_text)
        )
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return template_id
    except Exception as e:
        print(f"Error adding template: {e}")
        return None

def update_template(template_id: int, name: str = None, template_text: str = None) -> bool:
    """Обновить шаблон"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        if name and template_text:
            cursor.execute(
                "UPDATE templates SET name = ?, template_text = ? WHERE id = ?",
                (name, template_text, template_id)
            )
        elif name:
            cursor.execute("UPDATE templates SET name = ? WHERE id = ?", (name, template_id))
        elif template_text:
            cursor.execute("UPDATE templates SET template_text = ? WHERE id = ?", (template_text, template_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating template: {e}")
        return False

def remove_template(template_id: int) -> bool:
    """Удалить шаблон"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error removing template: {e}")
        return False

def get_template(template_id: int) -> Optional[Dict]:
    """Получить шаблон по ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_template_by_name(name: str) -> Optional[Dict]:
    """Получить шаблон по имени"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates WHERE name = ?", (name,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_templates() -> List[Dict]:
    """Получить все шаблоны"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def assign_template_to_channel(channel_id: str, template_id: int) -> bool:
    """Прикрепить шаблон к каналу"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO channel_templates (channel_id, template_id) VALUES (?, ?)",
            (channel_id, template_id)
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error assigning template to channel: {e}")
        return False

def unassign_template_from_channel(channel_id: str) -> bool:
    """Открепить шаблон от канала"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channel_templates WHERE channel_id = ?", (channel_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error unassigning template from channel: {e}")
        return False

def get_channel_template(channel_id: str) -> Optional[Dict]:
    """Получить шаблон канала"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.* FROM templates t
        JOIN channel_templates ct ON t.id = ct.template_id
        WHERE ct.channel_id = ?
    """, (channel_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None
