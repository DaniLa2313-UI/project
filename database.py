import sqlite3
from typing import List, Optional

DB_NAME = "catalog.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Создание таблиц и заполнение начальными данными."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            description TEXT DEFAULT '',
            category_id INTEGER,
            resource_type TEXT DEFAULT '',
            author TEXT DEFAULT '',
            year INTEGER,
            is_favorite INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        )
    """)

    # Начальные категории
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO categories (name) VALUES (?)",
                        [(n,) for n in ["Математика", "Информатика", "Физика",
                                        "Химия", "Биология", "Языки", "История"]])

    cur.execute("SELECT COUNT(*) FROM resources")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT INTO resources (title, url, description, category_id,
                                   resource_type, author, year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ("Khan Academy", "https://khanacademy.org",
             "Видеоуроки по математике и другим наукам", 1, "Видеокурс",
             "Khan Academy", 2020),
            ("Stepik", "https://stepik.org",
             "Платформа онлайн-курсов", 2, "Курс", "Stepik", 2021),
            ("Открытое образование", "https://openedu.ru",
             "Национальная платформа открытого образования", 1, "Курс",
             "Ассоциация", 2019),
            ("Фоксфорд", "https://foxford.ru",
             "Онлайн-школа для 1–11 классов", 3, "Курс", "Фоксфорд", 2018),
            ("Duolingo", "https://duolingo.com",
             "Изучение иностранных языков", 6, "Тренажёр", "Duolingo", 2022),
        ])

    conn.commit()
    conn.close()


# ---------- Категории ----------
def get_categories() -> List[sqlite3.Row]:
    conn = get_connection()
    rows = conn.execute("SELECT id, name FROM categories ORDER BY name").fetchall()
    conn.close()
    return rows


def add_category(name: str) -> bool:
    conn = get_connection()
    try:
        conn.execute("INSERT INTO categories (name) VALUES (?)", (name.strip(),))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def delete_category(cid: int) -> bool:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM categories WHERE id=?", (cid,))
        conn.commit()
        return True
    finally:
        conn.close()


def get_category_by_name(name: str) -> Optional[sqlite3.Row]:
    conn = get_connection()
    row = conn.execute("SELECT id, name FROM categories WHERE name=?",
                       (name,)).fetchone()
    conn.close()
    return row


# ---------- Ресурсы ----------
def get_resources(search: str = "", category_id: int = 0,
                  only_favorites: bool = False) -> List[sqlite3.Row]:
    conn = get_connection()
    query = """
        SELECT r.id, r.title, r.url, r.description, c.name AS category,
               r.resource_type, r.author, r.year, r.is_favorite,
               r.category_id
        FROM resources r
        LEFT JOIN categories c ON r.category_id = c.id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (r.title LIKE ? OR r.description LIKE ? OR r.author LIKE ?)"
        like = f"%{search}%"
        params += [like, like, like]
    if category_id:
        query += " AND r.category_id = ?"
        params.append(category_id)
    if only_favorites:
        query += " AND r.is_favorite = 1"
    query += " ORDER BY r.title COLLATE NOCASE"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows


def get_resource(rid: int) -> Optional[sqlite3.Row]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM resources WHERE id=?", (rid,)).fetchone()
    conn.close()
    return row


def add_resource(title, url, description, category_id,
                 resource_type, author, year) -> int:
    conn = get_connection()
    cur = conn.execute("""
        INSERT INTO resources (title, url, description, category_id,
                               resource_type, author, year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, url, description, category_id, resource_type, author, year))
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def update_resource(rid, title, url, description, category_id,
                    resource_type, author, year):
    conn = get_connection()
    conn.execute("""
        UPDATE resources
        SET title=?, url=?, description=?, category_id=?,
            resource_type=?, author=?, year=?
        WHERE id=?
    """, (title, url, description, category_id,
          resource_type, author, year, rid))
    conn.commit()
    conn.close()


def delete_resource(rid: int):
    conn = get_connection()
    conn.execute("DELETE FROM resources WHERE id=?", (rid,))
    conn.commit()
    conn.close()


def toggle_favorite(rid: int) -> bool:
    """Возвращает новое состояние is_favorite."""
    conn = get_connection()
    row = conn.execute("SELECT is_favorite FROM resources WHERE id=?",
                       (rid,)).fetchone()
    if not row:
        conn.close()
        return False
    new_val = 0 if row["is_favorite"] else 1
    conn.execute("UPDATE resources SET is_favorite=? WHERE id=?", (new_val, rid))
    conn.commit()
    conn.close()
    return bool(new_val)


def get_statistics() -> dict:
    conn = get_connection()
    stats = {}
    stats["total"] = conn.execute("SELECT COUNT(*) FROM resources").fetchone()[0]
    stats["favorites"] = conn.execute(
        "SELECT COUNT(*) FROM resources WHERE is_favorite=1").fetchone()[0]
    stats["categories"] = conn.execute(
        "SELECT COUNT(*) FROM categories").fetchone()[0]
    stats["by_category"] = conn.execute("""
        SELECT COALESCE(c.name, '— без категории —') AS name, COUNT(r.id) AS cnt
        FROM resources r
        LEFT JOIN categories c ON r.category_id = c.id
        GROUP BY r.category_id
        ORDER BY cnt DESC
    """).fetchall()
    conn.close()
    return stats