import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import webbrowser

import database as db


# ============================================================
#  Диалог добавления / редактирования ресурса
# ============================================================
class ResourceDialog(tk.Toplevel):
    def __init__(self, parent, title, rid=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("560x520")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.parent = parent
        self.rid = rid

        self._build()
        if rid:
            self._load(rid)
        self._center()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _build(self):
        pad = {"padx": 10, "pady": 5}

        ttk.Label(self, text="Название *").grid(row=0, column=0, sticky="w", **pad)
        self.title_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.title_var, width=50).grid(
            row=0, column=1, **pad)

        ttk.Label(self, text="URL *").grid(row=1, column=0, sticky="w", **pad)
        self.url_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.url_var, width=50).grid(
            row=1, column=1, **pad)

        ttk.Label(self, text="Описание").grid(row=2, column=0, sticky="nw", **pad)
        self.desc_text = tk.Text(self, width=50, height=5, wrap="word")
        self.desc_text.grid(row=2, column=1, **pad)

        ttk.Label(self, text="Категория").grid(row=3, column=0, sticky="w", **pad)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(
            self, textvariable=self.category_var,
            values=self._category_names(), state="readonly", width=47)
        self.category_combo.grid(row=3, column=1, **pad)

        ttk.Label(self, text="Тип ресурса").grid(row=4, column=0, sticky="w", **pad)
        self.type_var = tk.StringVar()
        ttk.Combobox(
            self, textvariable=self.type_var,
            values=["Курс", "Видеокурс", "Учебник", "Статья", "Тренажёр",
                    "Сборник задач", "Презентация", "Тест", "Другое"],
            width=47).grid(row=4, column=1, **pad)

        ttk.Label(self, text="Автор / Организация").grid(
            row=5, column=0, sticky="w", **pad)
        self.author_var = tk.StringVar()
        ttk.Entry(self, textvariable=self.author_var, width=50).grid(
            row=5, column=1, **pad)

        ttk.Label(self, text="Год").grid(row=6, column=0, sticky="w", **pad)
        self.year_var = tk.StringVar()
        ttk.Spinbox(self, from_=1990, to=2100, textvariable=self.year_var,
                    width=10).grid(row=6, column=1, sticky="w", **pad)

        ttk.Label(self, text="* — обязательные поля",
                  foreground="gray").grid(row=7, column=0, columnspan=2,
                                          sticky="w", padx=10)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=8, column=0, columnspan=2, pady=15)
        ttk.Button(btn_frame, text="💾 Сохранить",
                   command=self.save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Отмена",
                   command=self.destroy).pack(side="left", padx=5)

    @staticmethod
    def _category_names():
        return [c["name"] for c in db.get_categories()]

    def _load(self, rid):
        r = db.get_resource(rid)
        if not r:
            messagebox.showerror("Ошибка", "Ресурс не найден", parent=self)
            self.destroy()
            return
        self.title_var.set(r["title"])
        self.url_var.set(r["url"])
        self.desc_text.insert("1.0", r["description"] or "")
        if r["category_id"]:
            for c in db.get_categories():
                if c["id"] == r["category_id"]:
                    self.category_var.set(c["name"])
                    break
        self.type_var.set(r["resource_type"] or "")
        self.author_var.set(r["author"] or "")
        self.year_var.set(r["year"] or "")

    def save(self):
        title = self.title_var.get().strip()
        url = self.url_var.get().strip()

        if not title:
            messagebox.showerror("Ошибка", "Введите название ресурса", parent=self)
            return
        if not url:
            messagebox.showerror("Ошибка", "Введите URL ресурса", parent=self)
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            if not messagebox.askyesno(
                "URL без http",
                "URL не начинается с http:// или https://\n"
                "Продолжить сохранение?", parent=self):
                return

        cat_id = None
        cat_name = self.category_var.get().strip()
        if cat_name:
            row = db.get_category_by_name(cat_name)
            if row:
                cat_id = row["id"]
            else:
                db.add_category(cat_name)
                row = db.get_category_by_name(cat_name)
                cat_id = row["id"] if row else None

        year = None
        if self.year_var.get().strip():
            try:
                year = int(self.year_var.get())
                if not (1990 <= year <= 2100):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ошибка",
                                     "Год должен быть числом от 1990 до 2100",
                                     parent=self)
                return

        data = (title, url,
                self.desc_text.get("1.0", "end").strip(),
                cat_id,
                self.type_var.get().strip(),
                self.author_var.get().strip(),
                year)

        try:
            if self.rid:
                db.update_resource(self.rid, *data)
            else:
                db.add_resource(*data)
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e), parent=self)
            return

        self.parent.load_data()
        self.parent.set_status(
            "Ресурс обновлён" if self.rid else "Ресурс добавлен")
        self.destroy()


# ============================================================
#  Главное окно
# ============================================================
class CatalogApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Каталог электронных образовательных ресурсов")
        self.geometry("1200x680")
        self.minsize(1000, 560)

        db.init_db()

        self.sort_reverse = {}     # состояние сортировки по колонкам

        self._build_menu()
        self._build_toolbar()
        self._build_filter()
        self._build_table()
        self._build_statusbar()

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_categories()
        self.load_data()

    # ---------------- Меню ----------------
    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Добавить ресурс", accelerator="Ctrl+N",
                              command=self.add_item)
        file_menu.add_command(label="Импорт из CSV…", command=self.import_csv)
        file_menu.add_command(label="Экспорт в CSV…", accelerator="Ctrl+E",
                              command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Выход", command=self.on_close)
        menubar.add_cascade(label="Файл", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Редактировать", accelerator="F2",
                              command=self.edit_item)
        edit_menu.add_command(label="Удалить", accelerator="Delete",
                              command=self.delete_item)
        edit_menu.add_command(label="В избранное (Ctrl+D)",
                              command=self.toggle_favorite)
        menubar.add_cascade(label="Правка", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Обновить (F5)", command=self.load_data)
        view_menu.add_command(label="Сбросить фильтры", command=self.reset_filter)
        view_menu.add_command(label="Только избранное",
                              command=self.show_favorites)
        view_menu.add_separator()
        view_menu.add_command(label="Статистика", command=self.show_statistics)
        menubar.add_cascade(label="Вид", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="О программе", command=self.show_about)
        menubar.add_cascade(label="Справка", menu=help_menu)

        self.config(menu=menubar)

        # Горячие клавиши
        self.bind("<Control-n>", lambda e: self.add_item())
        self.bind("<Control-e>", lambda e: self.export_csv())
        self.bind("<Control-d>", lambda e: self.toggle_favorite())
        self.bind("<F2>", lambda e: self.edit_item())
        self.bind("<F5>", lambda e: self.load_data())
        self.bind("<Delete>", lambda e: self.delete_item())

    # ---------------- Панель инструментов ----------------
    def _build_toolbar(self):
        tb = ttk.Frame(self, padding=(5, 5))
        tb.pack(fill="x")

        def btn(text, cmd, width=None):
            b = ttk.Button(tb, text=text, command=cmd)
            if width:
                b.configure(width=width)
            b.pack(side="left", padx=2)
            return b

        btn("➕ Добавить", self.add_item)
        btn("✏️ Изменить", self.edit_item)
        btn("🗑 Удалить", self.delete_item)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6)
        btn("⭐ В избранное", self.toggle_favorite)
        btn("🌐 Открыть URL", self.open_url)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6)
        btn("📤 Экспорт CSV", self.export_csv)
        btn("📥 Импорт CSV", self.import_csv)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6)
        btn("➕ Категория", self.add_category)
        btn("🗑 Категория", self.delete_category)
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6)
        btn("📊 Статистика", self.show_statistics)
        btn("❓ О программе", self.show_about)

    # ---------------- Фильтры ----------------
    def _build_filter(self):
        frame = ttk.LabelFrame(self, text="Поиск и фильтрация", padding=8)
        frame.pack(fill="x", padx=5, pady=(0, 5))

        ttk.Label(frame, text="Поиск:").grid(row=0, column=0, sticky="w")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self.load_data())
        ttk.Entry(frame, textvariable=self.search_var, width=40).grid(
            row=0, column=1, padx=5)

        ttk.Label(frame, text="Категория:").grid(
            row=0, column=2, sticky="w", padx=(15, 0))
        self.category_var = tk.StringVar(value="Все")
        self.category_combo = ttk.Combobox(
            frame, textvariable=self.category_var, state="readonly", width=25)
        self.category_combo.grid(row=0, column=3, padx=5)
        self.category_combo.bind("<<ComboboxSelected>>",
                                 lambda e: self.load_data())

        self.fav_only_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(frame, text="Только избранное",
                        variable=self.fav_only_var,
                        command=self.load_data).grid(
            row=0, column=4, padx=15)

        ttk.Button(frame, text="🔄 Сбросить",
                   command=self.reset_filter).grid(row=0, column=5, padx=5)

    # ---------------- Таблица ----------------
    def _build_table(self):
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        columns = ("id", "fav", "title", "category", "type",
                   "author", "year", "url", "description")
        headings = ("ID", "⭐", "Название", "Категория", "Тип",
                    "Автор", "Год", "URL", "Описание")

        self.tree = ttk.Treeview(frame, columns=columns, show="headings",
                                 selectmode="browse")
        for col, head in zip(columns, headings):
            self.tree.heading(col, text=head,
                              command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=100, anchor="w")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("fav", width=40, anchor="center")
        self.tree.column("title", width=200)
        self.tree.column("category", width=120)
        self.tree.column("type", width=100)
        self.tree.column("author", width=130)
        self.tree.column("year", width=60, anchor="center")
        self.tree.column("url", width=220)
        self.tree.column("description", width=280)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=vsb.set, xscroll=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # События
        self.tree.bind("<Double-1>", lambda e: self.open_url())
        self.tree.bind("<Button-3>", self._show_context_menu)

        # Контекстное меню
        self.ctx_menu = tk.Menu(self, tearoff=0)
        self.ctx_menu.add_command(label="🌐 Открыть URL", command=self.open_url)
        self.ctx_menu.add_command(label="✏️ Редактировать", command=self.edit_item)
        self.ctx_menu.add_command(label="⭐ Переключить избранное",
                                  command=self.toggle_favorite)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="🗑 Удалить", command=self.delete_item)

    def _show_context_menu(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.ctx_menu.post(event.x_root, event.y_root)

    # ---------------- Строка состояния ----------------
    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(self, textvariable=self.status_var,
                  relief="sunken", anchor="w").pack(fill="x", side="bottom")

    def set_status(self, text):
        self.status_var.set(text)

    # ============================================================
    #  Логика
    # ============================================================
    def refresh_categories(self):
        self.categories = db.get_categories()
        values = ["Все"] + [c["name"] for c in self.categories]
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

        try:
            rows = db.get_resources(search, cat_id,
                                    only_favorites=self.fav_only_var.get())
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        for r in rows:
            star = "⭐" if r["is_favorite"] else ""
            self.tree.insert("", "end", values=(
                r["id"], star, r["title"], r["category"] or "",
                r["resource_type"] or "", r["author"] or "",
                r["year"] if r["year"] else "", r["url"],
                r["description"] or ""
            ))

        self.set_status(f"Показано: {len(rows)} из "
                        f"{db.get_statistics()['total']} ресурсов")

    def reset_filter(self):
        self.search_var.set("")
        self.category_var.set("Все")
        self.fav_only_var.set(False)
        self.load_data()

    def show_favorites(self):
        self.fav_only_var.set(True)
        self.load_data()

    def get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(self.tree.item(sel[0], "values")[0])
        except (ValueError, IndexError):
            return None

    def get_selected_url(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0], "values")[7]

    # ---------------- Действия ----------------
    def add_item(self):
        ResourceDialog(self, "Добавить ресурс")

    def edit_item(self):
        rid = self.get_selected_id()
        if rid is None:
            messagebox.showwarning("Внимание",
                                   "Выберите ресурс для редактирования")
            return
        ResourceDialog(self, "Редактировать ресурс", rid)

    def delete_item(self):
        rid = self.get_selected_id()
        if rid is None:
            messagebox.showwarning("Внимание", "Выберите ресурс для удаления")
            return
        sel = self.tree.selection()[0]
        title = self.tree.item(sel, "values")[2]
        if messagebox.askyesno("Подтверждение",
                               f"Удалить ресурс «{title}»?"):
            try:
                db.delete_resource(rid)
                self.load_data()
                self.set_status("Ресурс удалён")
            except Exception as e:
                messagebox.showerror("Ошибка БД", str(e))

    def toggle_favorite(self):
        rid = self.get_selected_id()
        if rid is None:
            messagebox.showwarning("Внимание", "Выберите ресурс")
            return
        state = db.toggle_favorite(rid)
        self.load_data()
        self.set_status("Добавлено в избранное ⭐" if state
                        else "Удалено из избранного")

    def open_url(self):
        url = self.get_selected_url()
        if not url:
            messagebox.showwarning("Внимание", "Выберите ресурс")
            return
        try:
            webbrowser.open(url)
            self.set_status(f"Открыт URL: {url}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть браузер:\n{e}")

    # ---------------- Категории ----------------
    def add_category(self):
        name = simpledialog.askstring("Новая категория",
                                      "Название категории:",
                                      parent=self)
        if not name:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning("Внимание", "Название не может быть пустым")
            return
        if db.add_category(name):
            self.refresh_categories()
            self.set_status(f"Категория «{name}» добавлена")
        else:
            messagebox.showerror("Ошибка", "Такая категория уже существует")

    def delete_category(self):
        cats = db.get_categories()
        if not cats:
            messagebox.showinfo("Информация", "Категорий нет")
            return

        # Диалог выбора категории
        dlg = tk.Toplevel(self)
        dlg.title("Удалить категорию")
        dlg.geometry("320x140")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="Выберите категорию:").pack(pady=8)
        var = tk.StringVar(value=cats[0]["name"])
        combo = ttk.Combobox(dlg, textvariable=var, state="readonly",
                             values=[c["name"] for c in cats], width=30)
        combo.pack(pady=5)

        def do_delete():
            name = var.get()
            cid = None
            for c in cats:
                if c["name"] == name:
                    cid = c["id"]
                    break
            if cid is None:
                return
            if not messagebox.askyesno(
                    "Подтверждение",
                    f"Удалить категорию «{name}»?\n"
                    f"Ресурсы останутся, но потеряют категорию.",
                    parent=dlg):
                return
            db.delete_category(cid)
            self.refresh_categories()
            self.load_data()
            self.set_status(f"Категория «{name}» удалена")
            dlg.destroy()

        btns = ttk.Frame(dlg)
        btns.pack(pady=10)
        ttk.Button(btns, text="Удалить", command=do_delete).pack(side="left", padx=5)
        ttk.Button(btns, text="Отмена", command=dlg.destroy).pack(side="left", padx=5)

    # ---------------- CSV ----------------
    def export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV файл", "*.csv")],
            initialfile="catalog.csv",
            title="Экспорт каталога")
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                writer.writerow(["ID", "Избранное", "Название", "Категория",
                                 "Тип", "Автор", "Год", "URL", "Описание"])
                for item in self.tree.get_children():
                    writer.writerow(self.tree.item(item, "values"))
            messagebox.showinfo("Готово",
                                f"Экспортировано {len(self.tree.get_children())} "
                                f"записей в\n{path}")
            self.set_status(f"Экспорт в {path}")
        except Exception as e:
            messagebox.showerror("Ошибка экспорта", str(e))

    def import_csv(self):
        path = filedialog.askopenfilename(
            filetypes=[("CSV файл", "*.csv")],
            title="Импорт каталога")
        if not path:
            return
        imported = 0
        errors = 0
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                # автоопределение разделителя
                sample = f.read(2048)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=";,")
                reader = csv.reader(f, dialect)
                header = next(reader, None)  # пропускаем заголовок

                for row in reader:
                    if len(row) < 3:
                        errors += 1
                        continue
                    # Ожидаем: ID;⭐;Название;Категория;Тип;Автор;Год;URL;Описание
                    if len(row) >= 9:
                        _, _, title, cat, rtype, author, year, url, desc = row[:9]
                    elif len(row) == 8:
                        _, title, cat, rtype, author, year, url, desc = row
                    else:
                        errors += 1
                        continue

                    title = title.strip()
                    url = url.strip()
                    if not title or not url:
                        errors += 1
                        continue

                    cat_id = None
                    cat = cat.strip()
                    if cat:
                        c = db.get_category_by_name(cat)
                        if c:
                            cat_id = c["id"]
                        else:
                            db.add_category(cat)
                            c = db.get_category_by_name(cat)
                            cat_id = c["id"] if c else None

                    try:
                        y = int(year) if str(year).strip() else None
                    except ValueError:
                        y = None

                    db.add_resource(title, url, desc.strip(), cat_id,
                                    rtype.strip(), author.strip(), y)
                    imported += 1

            self.refresh_categories()
            self.load_data()
            messagebox.showinfo("Импорт завершён",
                                f"Импортировано: {imported}\n"
                                f"Пропущено строк: {errors}")
            self.set_status(f"Импорт завершён: +{imported}")
        except Exception as e:
            messagebox.showerror("Ошибка импорта", str(e))

    # ---------------- Статистика ----------------
    def show_statistics(self):
        stats = db.get_statistics()

        dlg = tk.Toplevel(self)
        dlg.title("Статистика каталога")
        dlg.geometry("420x420")
        dlg.transient(self)
        dlg.grab_set()

        ttk.Label(dlg, text="📊 Статистика",
                  font=("Arial", 14, "bold")).pack(pady=10)

        info = ttk.Frame(dlg)
        info.pack(pady=5, fill="x", padx=15)
        ttk.Label(info, text=f"Всего ресурсов: {stats['total']}",
                  font=("Arial", 11)).pack(anchor="w")
        ttk.Label(info, text=f"В избранном: {stats['favorites']}",
                  font=("Arial", 11)).pack(anchor="w")
        ttk.Label(info, text=f"Категорий: {stats['categories']}",
                  font=("Arial", 11)).pack(anchor="w")

        ttk.Separator(dlg, orient="horizontal").pack(fill="x", padx=15, pady=10)
        ttk.Label(dlg, text="Распределение по категориям:",
                  font=("Arial", 11, "bold")).pack(anchor="w", padx=15)

        tree = ttk.Treeview(dlg, columns=("cat", "cnt"),
                            show="headings", height=10)
        tree.heading("cat", text="Категория")
        tree.heading("cnt", text="Кол-во")
        tree.column("cat", width=250)
        tree.column("cnt", width=80, anchor="center")
        tree.pack(fill="both", expand=True, padx=15, pady=5)

        for row in stats["by_category"]:
            tree.insert("", "end", values=(row["name"], row["cnt"]))

        ttk.Button(dlg, text="Закрыть",
                   command=dlg.destroy).pack(pady=10)

    # ---------------- О программе ----------------
    def show_about(self):
        messagebox.showinfo(
            "О программе",
            "Каталог электронных образовательных ресурсов\n\n"
            "Версия 2.0\n"
            "База данных: SQLite\n"
            "Интерфейс: Tkinter\n\n"
            "Возможности:\n"
            "• Добавление / редактирование / удаление ресурсов\n"
            "• Категории и избранное\n"
            "• Поиск, фильтрация, сортировка\n"
            "• Экспорт / импорт CSV\n"
            "• Статистика каталога\n\n"
            "Горячие клавиши:\n"
            "Ctrl+N — новый ресурс\n"
            "Ctrl+E — экспорт CSV\n"
            "Ctrl+D — в избранное\n"
            "F2 — редактировать\n"
            "F5 — обновить\n"
            "Delete — удалить")

    # ---------------- Сортировка ----------------
    def sort_by(self, col):
        items = [(self.tree.set(k, col), k) for k in self.tree.get_children("")]
        reverse = self.sort_reverse.get(col, False)

        def key_func(item):
            v = item[0].strip()
            if col in ("id", "year"):
                try:
                    return (0, int(v))
                except ValueError:
                    return (1, 0)
            return (0, v.lower())

        items.sort(key=key_func, reverse=reverse)
        for idx, (_, k) in enumerate(items):
            self.tree.move(k, "", idx)
        self.sort_reverse[col] = not reverse

    # ---------------- Закрытие ----------------
    def on_close(self):
        if messagebox.askyesno("Выход", "Закрыть приложение?"):
            self.destroy()


if __name__ == "__main__":
    app = CatalogApp()
    app.mainloop()

#test