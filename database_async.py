"""
Асинхронная версия работы с базой данных
Использует aiosqlite для неблокирующих операций
"""
import aiosqlite
import os
from datetime import datetime
from typing import List, Dict, Optional

DB_FILE = os.getenv("DATABASE_FILE", "bot_database.db")


async def get_connection():
    """Получить асинхронное соединение с БД"""
    conn = await aiosqlite.connect(DB_FILE)
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db():
    """Инициализация базы данных"""
    async with aiosqlite.connect(DB_FILE) as conn:
        # Таблица администраторов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                role TEXT NOT NULL DEFAULT 'junior',
                name TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица каналов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                channel_name TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица шаблонов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                template_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица связи каналов и шаблонов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS channel_templates (
                channel_id TEXT PRIMARY KEY,
                template_id INTEGER,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE,
                FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL
            )
        """)
        
        # Таблица связи админов и каналов
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_channels (
                admin_id INTEGER,
                channel_id TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (admin_id, channel_id),
                FOREIGN KEY (admin_id) REFERENCES admins(user_id) ON DELETE CASCADE,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
            )
        """)
        
        # Таблица статистики
        await conn.execute("""
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
        
        await conn.commit()


# ================== ADMIN FUNCTIONS ==================

async def add_admin(user_id: int, username: Optional[str] = None, role: str = 'junior', name: Optional[str] = None) -> bool:
    """Добавить или обновить администратора"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO admins (user_id, username, role, name) VALUES (?, ?, ?, ?)",
                (user_id, username, role, name)
            )
            await conn.execute(
                "UPDATE admins SET username = COALESCE(?, username), role = COALESCE(?, role), name = COALESCE(?, name) WHERE user_id = ?",
                (username, role, name, user_id)
            )
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error adding admin: {e}")
        return False


async def remove_admin(user_id: int) -> bool:
    """Удалить администратора"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error removing admin: {e}")
        return False


async def get_admin(user_id: int) -> Optional[Dict]:
    """Получить информацию об админе"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_admins() -> List[Dict]:
    """Получить список всех админов"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM admins ORDER BY added_at") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь админом"""
    admin = await get_admin(user_id)
    return admin is not None


# ================== CHANNEL FUNCTIONS ==================

async def add_channel(channel_id: str, channel_name: str) -> bool:
    """Добавить канал"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO channels (channel_id, channel_name) VALUES (?, ?)",
                (channel_id, channel_name)
            )
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error adding channel: {e}")
        return False


async def remove_channel(channel_id: str) -> bool:
    """Удалить канал"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error removing channel: {e}")
        return False


async def get_channel(channel_id: str) -> Optional[Dict]:
    """Получить информацию о канале"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_channels() -> List[Dict]:
    """Получить список всех каналов"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM channels ORDER BY added_at") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ================== ADMIN-CHANNEL ASSIGNMENT ==================

async def assign_admin_to_channel(admin_id: int, channel_id: str) -> bool:
    """Назначить админа на канал"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute(
                "INSERT OR IGNORE INTO admin_channels (admin_id, channel_id) VALUES (?, ?)",
                (admin_id, channel_id)
            )
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error assigning admin to channel: {e}")
        return False


async def unassign_admin_from_channel(admin_id: int, channel_id: str) -> bool:
    """Убрать админа с канала"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute(
                "DELETE FROM admin_channels WHERE admin_id = ? AND channel_id = ?",
                (admin_id, channel_id)
            )
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error unassigning admin from channel: {e}")
        return False


async def get_admin_channels(admin_id: int) -> List[Dict]:
    """Получить список каналов админа"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("""
            SELECT c.* FROM channels c
            JOIN admin_channels ac ON c.channel_id = ac.channel_id
            WHERE ac.admin_id = ?
            ORDER BY c.channel_name
        """, (admin_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ================== STATISTICS ==================

async def log_upload(admin_id: int, channel_id: str, title: str, season: int, episode: int, 
                    file_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
    """Записать загрузку в статистику"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute("""
                INSERT INTO upload_stats (admin_id, channel_id, title, season, episode, file_id, message_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (admin_id, channel_id, title, season, episode, file_id, message_id))
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error logging upload: {e}")
        return False


async def get_admin_stats(admin_id: int) -> Dict:
    """Получить статистику админа"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        
        # Общее количество
        async with conn.execute(
            "SELECT COUNT(*) as total FROM upload_stats WHERE admin_id = ?",
            (admin_id,)
        ) as cursor:
            total = (await cursor.fetchone())['total']
        
        # По каналам
        async with conn.execute("""
            SELECT c.channel_name, COUNT(*) as count
            FROM upload_stats us
            JOIN channels c ON us.channel_id = c.channel_id
            WHERE us.admin_id = ?
            GROUP BY c.channel_id
            ORDER BY count DESC
        """, (admin_id,)) as cursor:
            by_channel = [dict(row) for row in await cursor.fetchall()]
        
        return {
            'total': total,
            'by_channel': by_channel
        }


async def get_all_stats() -> List[Dict]:
    """Получить общую статистику всех админов"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("""
            SELECT 
                a.user_id,
                a.username,
                COUNT(us.id) as total_uploads
            FROM admins a
            LEFT JOIN upload_stats us ON a.user_id = us.admin_id
            GROUP BY a.user_id
            ORDER BY total_uploads DESC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ================== TEMPLATE FUNCTIONS ==================

async def add_template(name: str, template_text: str) -> Optional[int]:
    """Добавить шаблон"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            cursor = await conn.execute(
                "INSERT INTO templates (name, template_text) VALUES (?, ?)",
                (name, template_text)
            )
            template_id = cursor.lastrowid
            await conn.commit()
            return template_id
    except Exception as e:
        print(f"Error adding template: {e}")
        return None


async def update_template(template_id: int, name: str = None, template_text: str = None) -> bool:
    """Обновить шаблон"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            if name and template_text:
                await conn.execute(
                    "UPDATE templates SET name = ?, template_text = ? WHERE id = ?",
                    (name, template_text, template_id)
                )
            elif name:
                await conn.execute("UPDATE templates SET name = ? WHERE id = ?", (name, template_id))
            elif template_text:
                await conn.execute("UPDATE templates SET template_text = ? WHERE id = ?", (template_text, template_id))
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error updating template: {e}")
        return False


async def remove_template(template_id: int) -> bool:
    """Удалить шаблон"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute("DELETE FROM templates WHERE id = ?", (template_id,))
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error removing template: {e}")
        return False


async def get_template(template_id: int) -> Optional[Dict]:
    """Получить шаблон по ID"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM templates WHERE id = ?", (template_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_template_by_name(name: str) -> Optional[Dict]:
    """Получить шаблон по имени"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM templates WHERE name = ?", (name,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_all_templates() -> List[Dict]:
    """Получить все шаблоны"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("SELECT * FROM templates ORDER BY name") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def assign_template_to_channel(channel_id: str, template_id: int) -> bool:
    """Прикрепить шаблон к каналу"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO channel_templates (channel_id, template_id) VALUES (?, ?)",
                (channel_id, template_id)
            )
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error assigning template to channel: {e}")
        return False


async def unassign_template_from_channel(channel_id: str) -> bool:
    """Открепить шаблон от канала"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            await conn.execute("DELETE FROM channel_templates WHERE channel_id = ?", (channel_id,))
            await conn.commit()
        return True
    except Exception as e:
        print(f"Error unassigning template from channel: {e}")
        return False


async def get_channel_template(channel_id: str) -> Optional[Dict]:
    """Получить шаблон канала"""
    async with aiosqlite.connect(DB_FILE) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("""
            SELECT t.* FROM templates t
            JOIN channel_templates ct ON t.id = ct.template_id
            WHERE ct.channel_id = ?
        """, (channel_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None
