import os, json, datetime, threading, time
import customtkinter as ctk
from .base_module import BaseModule

TASKS_FILE = "tasks.json"

def _load_tasks():
    if not os.path.exists(TASKS_FILE):
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def _save_tasks(tasks):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2, ensure_ascii=False)

class TasksModule(BaseModule):
    name = "Tareas"
    icon = "📋"
    description = "Gestión de tareas con recordatorios y notificaciones"

    def __init__(self, app):
        super().__init__(app)
        self._tasks = _load_tasks()
        self._running = True
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()

    def build(self, parent):
        self._rebuild_ui(parent)

    def on_deactivate(self):
        _save_tasks(self._tasks)

    def _rebuild_ui(self, parent):
        for w in parent.winfo_children():
            w.destroy()

        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=15)

        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(header, text="📋 Gestión de Tareas", font=("Arial", 20, "bold"),
                     text_color=self.colors["accent"]).pack(side="left")

        stats = self._get_stats()
        ctk.CTkLabel(header, text=f"{stats['pending']} pendientes · {stats['completed']} completadas",
                     font=("Arial", 11), text_color=self.colors["text_secondary"]).pack(side="right")

        self._build_add_form(main)
        self._build_list(main)

    def _get_stats(self):
        pending = sum(1 for t in self._tasks if not t.get("done"))
        completed = sum(1 for t in self._tasks if t.get("done"))
        return {"pending": pending, "completed": completed}

    def _build_add_form(self, parent):
        form = ctk.CTkFrame(parent, fg_color=self.colors["fg"])
        form.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(form, text="Nueva tarea", font=("Arial", 13, "bold"),
                     text_color=self.colors["text"]).pack(anchor="w", padx=15, pady=(10, 5))

        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 10))

        self._title_entry = ctk.CTkEntry(row, placeholder_text="¿Qué hay que hacer?", fg_color=self.colors["bg"],
                                          text_color=self.colors["text"], border_color=self.colors["border"])
        self._title_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        priorities = ["Baja", "Normal", "Alta"]
        self._priority_var = ctk.StringVar(value="Normal")
        ctk.CTkOptionMenu(row, values=priorities, variable=self._priority_var,
                          fg_color=self.colors["bg"], button_color=self.colors["accent"],
                          text_color=self.colors["text"], width=90).pack(side="left", padx=(0, 8))

        ctk.CTkButton(row, text="➕ Añadir", command=self._add_task,
                      fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                      text_color=self.colors["text"], width=90).pack(side="left")

        row2 = ctk.CTkFrame(form, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(row2, text="Recordatorio:", font=("Arial", 11),
                     text_color=self.colors["text_secondary"]).pack(side="left", padx=(0, 8))

        self._date_entry = ctk.CTkEntry(row2, placeholder_text="2026-05-20", width=110,
                                        fg_color=self.colors["bg"], text_color=self.colors["text"],
                                        border_color=self.colors["border"])
        self._date_entry.pack(side="left", padx=(0, 5))

        self._time_entry = ctk.CTkEntry(row2, placeholder_text="14:30", width=80,
                                        fg_color=self.colors["bg"], text_color=self.colors["text"],
                                        border_color=self.colors["border"])
        self._time_entry.pack(side="left", padx=(0, 5))

        ctk.CTkLabel(row2, text="(opcional)", font=("Arial", 10),
                     text_color=self.colors["text_secondary"]).pack(side="left")

    def _add_task(self):
        title = self._title_entry.get().strip()
        if not title:
            self.app.toast.show("Escribe un título para la tarea", type="warning")
            return

        due_date = self._date_entry.get().strip()
        due_time = self._time_entry.get().strip()
        due_str = ""
        if due_date and due_time:
            due_str = f"{due_date} {due_time}"
        elif due_date:
            due_str = due_date

        task = {
            "id": int(time.time() * 1000),
            "title": title,
            "due": due_str,
            "priority": self._priority_var.get(),
            "done": False,
            "created": datetime.datetime.now().isoformat(),
            "notified": False,
        }

        self._tasks.append(task)
        _save_tasks(self._tasks)
        self._title_entry.delete(0, "end")
        self._date_entry.delete(0, "end")
        self._time_entry.delete(0, "end")
        self.app.toast.show(f"Tarea añadida: {title}", type="success")
        self._rebuild_ui(self._get_parent())

    def _get_parent(self):
        if self.content_frame and self.content_frame.winfo_exists():
            return self.content_frame.master
        return None

    def _build_list(self, parent):
        container = ctk.CTkScrollableFrame(parent, fg_color=self.colors["fg"])
        container.pack(fill="both", expand=True)

        pending = [t for t in self._tasks if not t.get("done")]
        completed = [t for t in self._tasks if t.get("done")]

        if not self._tasks:
            ctk.CTkLabel(container, text="No hay tareas. ¡Añade una arriba!",
                         font=("Arial", 12), text_color=self.colors["text_secondary"]).pack(pady=40)
            return

        if pending:
            ctk.CTkLabel(container, text=f"📌 Pendientes ({len(pending)})",
                         font=("Arial", 13, "bold"), text_color=self.colors["accent"],
                         anchor="w").pack(fill="x", padx=10, pady=(10, 5))
            for t in pending:
                self._render_task(container, t)

        if completed:
            ctk.CTkLabel(container, text=f"✅ Completadas ({len(completed)})",
                         font=("Arial", 13, "bold"), text_color=self.colors["success"],
                         anchor="w").pack(fill="x", padx=10, pady=(15, 5))
            for t in completed:
                self._render_task(container, t)

    def _render_task(self, parent, task):
        card = ctk.CTkFrame(parent, fg_color=self.colors["bg"], corner_radius=8)
        card.pack(fill="x", padx=10, pady=3)

        priority_colors = {"Alta": "#ff4444", "Normal": self.colors["accent"], "Baja": "#888888"}
        pcolor = priority_colors.get(task.get("priority", "Normal"), self.colors["accent"])

        done = task.get("done", False)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=12, pady=8)

        title_frame = ctk.CTkFrame(info, fg_color="transparent")
        title_frame.pack(fill="x")

        ctk.CTkLabel(title_frame, text="●", font=("Arial", 8), text_color=pcolor).pack(side="left", padx=(0, 6))

        title_text = task.get("title", "")
        if done:
            title_text = f"~~{title_text}~~"
        ctk.CTkLabel(title_frame, text=title_text, font=("Arial", 12, "overstrike" if done else "normal"),
                     text_color=self.colors["text_secondary"] if done else self.colors["text"],
                     anchor="w").pack(side="left")

        due = task.get("due", "")
        if due:
            ctk.CTkLabel(info, text=f"⏰ {due}", font=("Arial", 10),
                         text_color=self.colors["text_secondary"], anchor="w").pack(fill="x", padx=(14, 0))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(side="right", padx=8, pady=8)

        if not done:
            ctk.CTkButton(btns, text="✅", width=32, height=28, fg_color="transparent",
                          hover_color=self.colors["hover"], text_color=self.colors["success"],
                          command=lambda t=task: self._toggle_done(t)).pack(side="left", padx=2)
        else:
            ctk.CTkButton(btns, text="↩️", width=32, height=28, fg_color="transparent",
                          hover_color=self.colors["hover"], text_color=self.colors["text_secondary"],
                          command=lambda t=task: self._toggle_done(t)).pack(side="left", padx=2)

        ctk.CTkButton(btns, text="🗑️", width=32, height=28, fg_color="transparent",
                      hover_color=self.colors["hover"], text_color=self.colors["error"],
                      command=lambda t=task: self._delete_task(t)).pack(side="left", padx=2)

    def _toggle_done(self, task):
        task["done"] = not task.get("done", False)
        _save_tasks(self._tasks)
        self._rebuild_ui(self._get_parent())
        status = "completada" if task["done"] else "reactivada"
        self.app.toast.show(f"Tarea {status}: {task['title']}", type="success")

    def _delete_task(self, task):
        self._tasks = [t for t in self._tasks if t.get("id") != task.get("id")]
        _save_tasks(self._tasks)
        self._rebuild_ui(self._get_parent())
        self.app.toast.show(f"Tarea eliminada: {task['title']}", type="info")

    def _scheduler_loop(self):
        while self._running:
            try:
                now = datetime.datetime.now()
                for task in self._tasks:
                    if task.get("done") or task.get("notified"):
                        continue
                    due = task.get("due", "")
                    if not due:
                        continue
                    try:
                        for fmt in ["%Y-%m-%d %H:%M", "%Y-%m-%d"]:
                            try:
                                due_dt = datetime.datetime.strptime(due, fmt)
                                break
                            except:
                                continue
                        else:
                            continue
                        if now >= due_dt:
                            task["notified"] = True
                            _save_tasks(self._tasks)
                            title = task.get("title", "Sin título")
                            self.app.after(0, lambda t=title: self.app.toast.show(
                                f"⏰ Recordatorio: {t}", type="warning", duration=8
                            ))
                    except:
                        continue
            except:
                pass
            time.sleep(30)

    def __del__(self):
        self._running = False
        _save_tasks(self._tasks)
