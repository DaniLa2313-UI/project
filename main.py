import sqlite3
from typing import List, Tuple

DB_NAME = "catalog.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Создание таблиц и заполнение начальными данными"""
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
            description TEXT,
            category_id INTEGER,
            resource_type TEXT,
            author TEXT,
            year INTEGER,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    """)

    # Начальные категории
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] == 0:
        categories = [
            ("Математика",), ("Информатика",), ("Физика",),
            ("Химия",), ("Биология",), ("Языки",), ("История",)
        ]
        cur.executemany("INSERT INTO categories (name) VALUES (?)", categories)

        # Примеры ресурсов
        resources = [
            ("Khan Academy", "https://khanacademy.org", "Видеоуроки по математике и другим наукам", 1, "Видеокурс", "Khan Academy", 2020),
            ("Stepik", "https://stepik.org", "Платформа онлайн-курсов", 2, "Курс", "Stepik", 2021),
            ("Открытое образование", "https://openedu.ru", "Национальная платформа открытого образования", 1, "Курс", "Ассоциация", 2019),
        ]
        cur.executemany("""
            INSERT INTO resources (title, url, description, category_id, resource_type, author, year)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, resources)

    conn.commit()
    conn.close()


def get_categories() -> List[Tuple]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def get_resources(search: str = "", category_id: int = 0) -> List[Tuple]:
    conn = get_connection()
    cur = conn.cursor()
    query = """
        SELECT r.id, r.title, r.url, r.description, c.name,
               r.resource_type, r.author, r.year
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
    query += " ORDER BY r.title"

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def add_resource(title, url, description, category_id, resource_type, author, year):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO resources (title, url, description, category_id, resource_type, author, year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, url, description, category_id, resource_type, author, year))
    conn.commit()
    conn.close()


def update_resource(rid, title, url, description, category_id, resource_type, author, year):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE resources
        SET title=?, url=?, description=?, category_id=?, resource_type=?, author=?, year=?
        WHERE id=?
    """, (title, url, description, category_id, resource_type, author, year, rid))
    conn.commit()
    conn.close()


def delete_resource(rid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM resources WHERE id=?", (rid,))
    conn.commit()
    conn.close()


def add_category(name):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog
        import webbrowser
        import csv

        import database as db

        class CatalogApp(tk.Tk):
            def __init__(self):
                super().__init__()
                self.title("Каталог электронных образовательных ресурсов")
                self.geometry("1100x650")
                self.minsize(900, 550)

                db.init_db()

                self._build_toolbar()
                self._build_filter()
                self._build_table()
                self._build_statusbar()

                self.load_data()

            # ---------- Построение интерфейса ----------
            def _build_toolbar(self):
                toolbar = ttk.Frame(self, padding=5)
                toolbar.pack(fill="x")

                ttk.Button(toolbar, text="➕ Добавить", command=self.add_item).pack(side="left", padx=2)
                ttk.Button(toolbar, text="✏️ Редактировать", command=self.edit_item).pack(side="left", padx=2)
                ttk.Button(toolbar, text="🗑 Удалить", command=self.delete_item).pack(side="left", padx=2)
                ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
                ttk.Button(toolbar, text="🌐 Открыть в браузере", command=self.open_url).pack(side="left", padx=2)
                ttk.Button(toolbar, text="📤 Экспорт CSV", command=self.export_csv).pack(side="left", padx=2)
                ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
                ttk.Button(toolbar, text="➕ Категория", command=self.add_category).pack(side="left", padx=2)

            def _build_filter(self):
                frame = ttk.LabelFrame(self, text="Поиск и фильтрация", padding=8)
                frame.pack(fill="x", padx=5, pady=5)

                ttk.Label(frame, text="Поиск:").grid(row=0, column=0, sticky="w")
                self.search_var = tk.StringVar()
                entry = ttk.Entry(frame, textvariable=self.search_var, width=40)
                entry.grid(row=0, column=1, padx=5)
                entry.bind("<KeyRelease>", lambda e: self.load_data())

                ttk.Label(frame, text="Категория:").grid(row=0, column=2, sticky="w", padx=(15, 0))
                self.category_var = tk.StringVar(value="Все")
                self.category_combo = ttk.Combobox(frame, textvariable=self.category_var,
                                                   state="readonly", width=25)
                self.category_combo.grid(row=0, column=3, padx=5)
                self.category_combo.bind("<<ComboboxSelected>>", lambda e: self.load_data())

                ttk.Button(frame, text="Сбросить", command=self.reset_filter).grid(row=0, column=4, padx=5)

                self.refresh_categories()

            def _build_table(self):
                frame = ttk.Frame(self)
                frame.pack(fill="both", expand=True, padx=5, pady=5)

                columns = ("id", "title", "category", "type", "author", "year", "url", "description")
                headings = ("ID", "Название", "Категория", "Тип", "Автор", "Год", "URL", "Описание")

                self.tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
                for col, head in zip(columns, headings):
                    self.tree.heading(col, text=head, command=lambda c=col: self.sort_by(c))
                    self.tree.column(col, width=100, anchor="w")

                self.tree.column("id", width=50, anchor="center")
                self.tree.column("title", width=200)
                self.tree.column("category", width=120)
                self.tree.column("type", width=100)
                self.tree.column("author", width=130)
                self.tree.column("year", width=60, anchor="center")
                self.tree.column("url", width=200)
                self.tree.column("description", width=250)

                vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
                hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
                self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

                self.tree.grid(row=0, column=0, sticky="nsew")
                vsb.grid(row=0, column=1, sticky="ns")
                hsb.grid(row=1, column=0, sticky="ew")

                frame.rowconfigure(0, weight=1)
                frame.columnconfigure(0, weight=1)

                self.tree.bind("<Double-1>", lambda e: self.open_url())

            def _build_statusbar(self):
                self.status_var = tk.StringVar()
                status = ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w")
                status.pack(fill="x", side="bottom")

            # ---------- Логика ----------
            def refresh_categories(self):
                categories = db.get_categories()
                self.categories = categories
                values = ["Все"] + [c["name"] for c in categories]
                self.category_combo["values"] = values
                if self.category_var.get() not in values:
                    self.category_var.set("Все")

            def load_data(self):
                search = self.search_var.get().strip()
                cat_name = self.category_var.get()
                cat_id = 0
                if cat_name and cat_name != "Все":
                    for c in self.categories:
                        if c["name"] == cat_name:
                            cat_id = c["id"]
                            break

                self.tree.delete(*self.tree.get_children())
                rows = db.get_resources(search, cat_id)
                for r in rows:
                    self.tree.insert("", "end", values=(
                        r["id"], r["title"], r["name"] or "", r["resource_type"] or "",
                        r["author"] or "", r["year"] or "", r["url"], r["description"] or ""
                    ))
                self.status_var.set(f"Найдено ресурсов: {len(rows)}")

            def reset_filter(self):
                self.search_var.set("")
                self.category_var.set("Все")
                self.load_data()

            def get_selected_id(self):
                sel = self.tree.selection()
                if not sel:
                    return None
                return int(self.tree.item(sel[0], "values")[0])

            def get_selected_url(self):
                sel = self.tree.selection()
                if not sel:
                    return None
                return self.tree.item(sel[0], "values")[6]

            def add_item(self):
                ResourceDialog(self, "Добавить ресурс")

            def edit_item(self):
                rid = self.get_selected_id()
                if rid is None:
                    messagebox.showwarning("Внимание", "Выберите ресурс для редактирования")
                    return
                ResourceDialog(self, "Редактировать ресурс", rid)

            def delete_item(self):
                rid = self.get_selected_id()
                if rid is None:
                    messagebox.showwarning("Внимание", "Выберите ресурс для удаления")
                    return
                if messagebox.askyesno("Подтверждение", "Удалить выбранный ресурс?"):
                    db.delete_resource(rid)
                    self.load_data()

            def open_url(self):
                url = self.get_selected_url()
                if url:
                    webbrowser.open(url)

            def add_category(self):
                name = simpledialog.askstring("Новая категория", "Название категории:")
                if not name:
                    return
                if db.add_category(name.strip()):
                    self.refresh_categories()
                    messagebox.showinfo("Успех", "Категория добавлена")
                else:
                    messagebox.showerror("Ошибка", "Такая категория уже существует")

            def export_csv(self):
                path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                    filetypes=[("CSV", "*.csv")],
                                                    initialfile="catalog.csv")
                if not path:
                    return
                with open(path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f, delimiter=";")
                    writer.writerow(["ID", "Название", "Категория", "Тип", "Автор", "Год", "URL", "Описание"])
                    for item in self.tree.get_children():
                        writer.writerow(self.tree.item(item, "values"))
                messagebox.showinfo("Готово", f"Экспортировано в {path}")

            def sort_by(self, col):
                items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]

                def try_int(v):
                    try:
                        return int(v)
                    except ValueError:
                        return v

                items.sort(key=lambda t: try_int(t[0]))
                for idx, (_, k) in enumerate(items):
                    self.tree.move(k, "", idx)

        # ---------- Диалог добавления/редактирования ----------
        class ResourceDialog(tk.Toplevel):
            def __init__(self, parent, title, rid=None):
                super().__init__(parent)
                self.title(title)
                self.geometry("500x480")
                self.resizable(False, False)
                self.transient(parent)
                self.grab_set()
                self.rid = rid
                self.parent = parent

                self._build()
                if rid:
                    self._load(rid)

            def _build(self):
                pad = {"padx": 8, "pady": 4}

                ttk.Label(self, text="Название *").grid(row=0, column=0, sticky="w", **pad)
                self.title_var = tk.StringVar()
                ttk.Entry(self, textvariable=self.title_var, width=50).grid(row=0, column=1, **pad)

                ttk.Label(self, text="URL *").grid(row=1, column=0, sticky="w", **pad)
                self.url_var = tk.StringVar()
                ttk.Entry(self, textvariable=self.url_var, width=50).grid(row=1, column=1, **pad)

                ttk.Label(self, text="Описание").grid(row=2, column=0, sticky="nw", **pad)
                self.desc_text = tk.Text(self, width=50, height=5)
                self.desc_text.grid(row=2, column=1, **pad)

                ttk.Label(self, text="Категория").grid(row=3, column=0, sticky="w", **pad)
                self.category_var = tk.StringVar()
                cats = [c["name"] for c in db.get_categories()]
                self.category_combo = ttk.Combobox(self, textvariable=self.category_var,
                                                   values=cats, state="readonly", width=47)
                self.category_combo.grid(row=3, column=1, **pad)

                ttk.Label(self, text="Тип ресурса").grid(row=4, column=0, sticky="w", **pad)
                self.type_var = tk.StringVar()
                ttk.Combobox(self, textvariable=self.type_var,
                             values=["Курс", "Видеокурс", "Учебник", "Статья", "Тренажёр",
                                     "Сборник задач", "Презентация", "Тест", "Другое"],
                             width=47).grid(row=4, column=1, **pad)

                ttk.Label(self, text="Автор / Организация").grid(row=5, column=0, sticky="w", **pad)
                self.author_var = tk.StringVar()
                ttk.Entry(self, textvariable=self.author_var, width=50).grid(row=5, column=1, **pad)

                ttk.Label(self, text="Год").grid(row=6, column=0, sticky="w", **pad)
                self.year_var = tk.StringVar()
                ttk.Spinbox(self, from_=1990, to=2100, textvariable=self.year_var,
                            width=10).grid(row=6, column=1, sticky="w", **pad)

                btn_frame = ttk.Frame(self)
                btn_frame.grid(row=7, column=0, columnspan=2, pady=15)
                ttk.Button(btn_frame, text="Сохранить", command=self.save).pack(side="left", padx=5)
                ttk.Button(btn_frame, text="Отмена", command=self.destroy).pack(side="left", padx=5)

            def _load(self, rid):
                rows = db.get_resources()
                for r in rows:
                    if r["id"] == rid:
                        self.title_var.set(r["title"])
                        self.url_var.set(r["url"])
                        self.desc_text.insert("1.0", r["description"] or "")
                        self.category_var.set(r["name"] or "")
                        self.type_var.set(r["resource_type"] or "")
                        self.author_var.set(r["author"] or "")
                        self.year_var.set(r["year"] or "")
                        break

            def save(self):
                title = self.title_var.get().strip()
                url = self.url_var.get().strip()
                if not title or not url:
                    messagebox.showerror("Ошибка", "Поля «Название» и «URL» обязательны")
                    return

                cat_id = None
                cat_name = self.category_var.get()
                for c in db.get_categories():
                    if c["name"] == cat_name:
                        cat_id = c["id"]
                        break

                try:
                    year = int(self.year_var.get()) if self.year_var.get() else None
                except ValueError:
                    year = None

                data = (title, url, self.desc_text.get("1.0", "end").strip(),
                        cat_id, self.type_var.get(), self.author_var.get().strip(), year)

                if self.rid:
                    db.update_resource(self.rid, *data)
                else:
                    db.add_resource(*data)

                self.parent.load_data()
                self.destroy()

        # Для simpledialog
        from tkinter import simpledialog

        if __name__ == "__main__":
            app = CatalogApp()
            app.mainloop()