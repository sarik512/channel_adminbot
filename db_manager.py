#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер базы данных бота
Полное управление: админы, каналы, шаблоны, статистика

Использование:
    python db_manager.py
"""

import sqlite3
from datetime import datetime

DATABASE = 'bot_database.db'

# ==================== УТИЛИТЫ ====================

def connect_db():
    """Подключение к базе данных"""
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к базе: {e}")
        return None

# ==================== СТАТИСТИКА ====================

def show_stats():
    """Показать статистику"""
    conn = connect_db()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    print("\n" + "=" * 80)
    print("📊 СТАТИСТИКА ЗАГРУЗОК")
    print("=" * 80)
    
    # Общая статистика
    cursor.execute("SELECT COUNT(*) as total FROM upload_stats")
    total = cursor.fetchone()['total']
    print(f"\nВсего загрузок: {total}\n")
    
    # По админам
    cursor.execute("""
        SELECT 
            a.user_id,
            a.username,
            COUNT(us.id) as uploads
        FROM admins a
        LEFT JOIN upload_stats us ON a.user_id = us.admin_id
        GROUP BY a.user_id
        ORDER BY uploads DESC
    """)
    
    print("По админам:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"  • {row['username']} (ID: {row['user_id']}): {row['uploads']} загрузок")
    
    # По каналам
    cursor.execute("""
        SELECT 
            c.channel_id,
            c.channel_name,
            COUNT(us.id) as uploads
        FROM channels c
        LEFT JOIN upload_stats us ON c.channel_id = us.channel_id
        GROUP BY c.channel_id
        ORDER BY uploads DESC
    """)
    
    print("\nПо каналам:")
    print("-" * 80)
    for row in cursor.fetchall():
        print(f"  • {row['channel_name']} ({row['channel_id']}): {row['uploads']} загрузок")
    
    print("=" * 80)
    conn.close()

def add_stats(admin_id, channel_id, count, title="Загрузки до бота"):
    """Добавить статистику"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        # Проверки
        cursor.execute("SELECT username FROM admins WHERE user_id = ?", (admin_id,))
        admin = cursor.fetchone()
        if not admin:
            print(f"❌ Админ с ID {admin_id} не найден!")
            return False
        
        cursor.execute("SELECT channel_name FROM channels WHERE channel_id = ?", (channel_id,))
        channel = cursor.fetchone()
        if not channel:
            print(f"❌ Канал {channel_id} не найден!")
            return False
        
        # Добавление
        uploaded_at = datetime.now()
        for i in range(1, count + 1):
            cursor.execute("""
                INSERT INTO upload_stats (admin_id, channel_id, title, season, episode, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (admin_id, channel_id, title, 0, i, uploaded_at))
        
        conn.commit()
        print(f"\n✅ Добавлено {count} загрузок для {admin['username']}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def clear_stats(admin_id=None):
    """Очистить статистику"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        if admin_id:
            cursor.execute("SELECT username FROM admins WHERE user_id = ?", (admin_id,))
            admin = cursor.fetchone()
            if not admin:
                print(f"❌ Админ не найден!")
                return False
            
            cursor.execute("SELECT COUNT(*) FROM upload_stats WHERE admin_id = ?", (admin_id,))
            count = cursor.fetchone()[0]
            
            confirm = input(f"\n⚠️  Удалить {count} записей для {admin['username']}? (да/нет): ").strip().lower()
            if confirm != 'да':
                print("❌ Отменено")
                return False
            
            cursor.execute("DELETE FROM upload_stats WHERE admin_id = ?", (admin_id,))
            print(f"✅ Удалено {count} записей")
        else:
            cursor.execute("SELECT COUNT(*) FROM upload_stats")
            count = cursor.fetchone()[0]
            
            confirm1 = input(f"\n⚠️  Удалить ВСЮ статистику ({count} записей)? (да/нет): ").strip().lower()
            if confirm1 != 'да':
                print("❌ Отменено")
                return False
            
            confirm2 = input("Подтвердите еще раз (да/нет): ").strip().lower()
            if confirm2 != 'да':
                print("❌ Отменено")
                return False
            
            cursor.execute("DELETE FROM upload_stats")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name='upload_stats'")
            print(f"✅ Удалено {count} записей")
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ==================== АДМИНЫ ====================

def list_admins():
    """Список админов"""
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins ORDER BY user_id")
    admins = cursor.fetchall()
    
    print("\n" + "=" * 80)
    print("👥 СПИСОК АДМИНОВ")
    print("=" * 80)
    
    if not admins:
        print("  ❌ Нет админов")
    else:
        for admin in admins:
            print(f"  • {admin['username']} (ID: {admin['user_id']})")
    
    print("=" * 80)
    conn.close()
    return admins

def add_admin(user_id, username):
    """Добавить админа"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        if cursor.fetchone():
            print(f"❌ Админ с ID {user_id} уже существует!")
            return False
        
        cursor.execute("""
            INSERT INTO admins (user_id, username, added_at)
            VALUES (?, ?, ?)
        """, (user_id, username, datetime.now()))
        
        conn.commit()
        print(f"✅ Админ {username} (ID: {user_id}) добавлен!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def remove_admin(user_id):
    """Удалить админа"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT username FROM admins WHERE user_id = ?", (user_id,))
        admin = cursor.fetchone()
        if not admin:
            print(f"❌ Админ не найден!")
            return False
        
        confirm = input(f"\n⚠️  Удалить админа {admin['username']}? (да/нет): ").strip().lower()
        if confirm != 'да':
            print("❌ Отменено")
            return False
        
        cursor.execute("DELETE FROM admins WHERE user_id = ?", (user_id,))
        conn.commit()
        print(f"✅ Админ {admin['username']} удален!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ==================== КАНАЛЫ ====================

def list_channels():
    """Список каналов"""
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels ORDER BY channel_name")
    channels = cursor.fetchall()
    
    print("\n" + "=" * 80)
    print("📺 СПИСОК КАНАЛОВ")
    print("=" * 80)
    
    if not channels:
        print("  ❌ Нет каналов")
    else:
        for channel in channels:
            print(f"  • {channel['channel_name']} ({channel['channel_id']})")
    
    print("=" * 80)
    conn.close()
    return channels

def add_channel(channel_id, channel_name):
    """Добавить канал"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
        if cursor.fetchone():
            print(f"❌ Канал {channel_id} уже существует!")
            return False
        
        cursor.execute("""
            INSERT INTO channels (channel_id, channel_name, added_at)
            VALUES (?, ?, ?)
        """, (channel_id, channel_name, datetime.now()))
        
        conn.commit()
        print(f"✅ Канал {channel_name} ({channel_id}) добавлен!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def remove_channel(channel_id):
    """Удалить канал"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT channel_name FROM channels WHERE channel_id = ?", (channel_id,))
        channel = cursor.fetchone()
        if not channel:
            print(f"❌ Канал не найден!")
            return False
        
        confirm = input(f"\n⚠️  Удалить канал {channel['channel_name']}? (да/нет): ").strip().lower()
        if confirm != 'да':
            print("❌ Отменено")
            return False
        
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
        conn.commit()
        print(f"✅ Канал {channel['channel_name']} удален!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ==================== ШАБЛОНЫ ====================

def list_templates():
    """Список шаблонов"""
    conn = connect_db()
    if not conn:
        return []
    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM templates ORDER BY name")
    templates = cursor.fetchall()
    
    print("\n" + "=" * 80)
    print("📝 СПИСОК ШАБЛОНОВ")
    print("=" * 80)
    
    if not templates:
        print("  ❌ Нет шаблонов")
    else:
        for template in templates:
            print(f"  • {template['name']} (ID: {template['id']})")
    
    print("=" * 80)
    conn.close()
    return templates

def add_template(name, text):
    """Добавить шаблон"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM templates WHERE name = ?", (name,))
        if cursor.fetchone():
            print(f"❌ Шаблон '{name}' уже существует!")
            return False
        
        cursor.execute("""
            INSERT INTO templates (name, template_text, created_at)
            VALUES (?, ?, ?)
        """, (name, text, datetime.now()))
        
        conn.commit()
        print(f"✅ Шаблон '{name}' добавлен!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def remove_template(template_id):
    """Удалить шаблон"""
    conn = connect_db()
    if not conn:
        return False
    
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM templates WHERE id = ?", (template_id,))
        template = cursor.fetchone()
        if not template:
            print(f"❌ Шаблон не найден!")
            return False
        
        confirm = input(f"\n⚠️  Удалить шаблон '{template['name']}'? (да/нет): ").strip().lower()
        if confirm != 'да':
            print("❌ Отменено")
            return False
        
        cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        conn.commit()
        print(f"✅ Шаблон '{template['name']}' удален!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

# ==================== МЕНЮ ====================

def show_main_menu():
    """Главное меню"""
    print("\n" + "=" * 80)
    print("🗄️  МЕНЕДЖЕР БАЗЫ ДАННЫХ БОТА")
    print("=" * 80)
    print("\n1. 📊 Управление статистикой")
    print("2. 👥 Управление админами")
    print("3. 📺 Управление каналами")
    print("4. 📝 Управление шаблонами")
    print("5. 📋 Показать всё")
    print("0. ❌ Выход")
    print("\n" + "=" * 80)

def stats_menu():
    """Меню статистики"""
    while True:
        print("\n" + "=" * 80)
        print("📊 УПРАВЛЕНИЕ СТАТИСТИКОЙ")
        print("=" * 80)
        print("\n1. Показать статистику")
        print("2. Добавить загрузки админу")
        print("3. Очистить статистику админа")
        print("4. Очистить всю статистику")
        print("0. Назад")
        print("\n" + "=" * 80)
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            show_stats()
        elif choice == '2':
            list_admins()
            list_channels()
            admin_id = input("\nID админа: ").strip()
            channel_id = input("ID канала: ").strip()
            count = input("Количество загрузок: ").strip()
            title = input("Название (Enter для 'Загрузки до бота'): ").strip() or "Загрузки до бота"
            try:
                if add_stats(int(admin_id), channel_id, int(count), title):
                    show_stats()
            except ValueError:
                print("❌ Неверный формат")
        elif choice == '3':
            list_admins()
            admin_id = input("\nID админа: ").strip()
            try:
                if clear_stats(int(admin_id)):
                    show_stats()
            except ValueError:
                print("❌ Неверный ID")
        elif choice == '4':
            if clear_stats():
                show_stats()
        elif choice == '0':
            break
        else:
            print("❌ Неверный выбор")

def admins_menu():
    """Меню админов"""
    while True:
        print("\n" + "=" * 80)
        print("👥 УПРАВЛЕНИЕ АДМИНАМИ")
        print("=" * 80)
        print("\n1. Показать список")
        print("2. Добавить админа")
        print("3. Удалить админа")
        print("0. Назад")
        print("\n" + "=" * 80)
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            list_admins()
        elif choice == '2':
            user_id = input("\nTelegram ID: ").strip()
            username = input("Username: ").strip()
            try:
                add_admin(int(user_id), username)
            except ValueError:
                print("❌ Неверный ID")
        elif choice == '3':
            list_admins()
            user_id = input("\nID админа для удаления: ").strip()
            try:
                remove_admin(int(user_id))
            except ValueError:
                print("❌ Неверный ID")
        elif choice == '0':
            break
        else:
            print("❌ Неверный выбор")

def channels_menu():
    """Меню каналов"""
    while True:
        print("\n" + "=" * 80)
        print("📺 УПРАВЛЕНИЕ КАНАЛАМИ")
        print("=" * 80)
        print("\n1. Показать список")
        print("2. Добавить канал")
        print("3. Удалить канал")
        print("0. Назад")
        print("\n" + "=" * 80)
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            list_channels()
        elif choice == '2':
            channel_id = input("\nID канала (@channel или -100...): ").strip()
            channel_name = input("Название канала: ").strip()
            add_channel(channel_id, channel_name)
        elif choice == '3':
            list_channels()
            channel_id = input("\nID канала для удаления: ").strip()
            remove_channel(channel_id)
        elif choice == '0':
            break
        else:
            print("❌ Неверный выбор")

def templates_menu():
    """Меню шаблонов"""
    while True:
        print("\n" + "=" * 80)
        print("📝 УПРАВЛЕНИЕ ШАБЛОНАМИ")
        print("=" * 80)
        print("\n1. Показать список")
        print("2. Добавить шаблон")
        print("3. Удалить шаблон")
        print("0. Назад")
        print("\n" + "=" * 80)
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            list_templates()
        elif choice == '2':
            name = input("\nНазвание шаблона: ").strip()
            print("Текст шаблона (Enter дважды для завершения):")
            lines = []
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
            text = "\n".join(lines)
            add_template(name, text)
        elif choice == '3':
            list_templates()
            template_id = input("\nID шаблона для удаления: ").strip()
            try:
                remove_template(int(template_id))
            except ValueError:
                print("❌ Неверный ID")
        elif choice == '0':
            break
        else:
            print("❌ Неверный выбор")

def show_all():
    """Показать всё"""
    list_admins()
    list_channels()
    list_templates()
    show_stats()

def main():
    """Главная функция"""
    print("\n" + "=" * 80)
    print("🗄️  МЕНЕДЖЕР БАЗЫ ДАННЫХ БОТА")
    print("=" * 80)
    print("\n⚠️  ВАЖНО: Остановите бота перед использованием!")
    print("   (Нажмите Ctrl+C в терминале с ботом)\n")
    
    input("Нажмите Enter для продолжения...")
    
    while True:
        show_main_menu()
        choice = input("\nВыберите раздел: ").strip()
        
        if choice == '1':
            stats_menu()
        elif choice == '2':
            admins_menu()
        elif choice == '3':
            channels_menu()
        elif choice == '4':
            templates_menu()
        elif choice == '5':
            show_all()
        elif choice == '0':
            print("\n👋 До свидания!\n")
            break
        else:
            print("❌ Неверный выбор")

if __name__ == '__main__':
    try:
        main()
        print("\n✅ Готово! Теперь можете запустить бота: python main.py\n")
    except KeyboardInterrupt:
        print("\n\n👋 Прервано пользователем\n")
