import os, json, datetime, threading
import customtkinter as ctk
from .base_module import BaseModule
from core.logger import get_logger

logger = get_logger("notas")

NOTES_DIR = "notes"
NOTES_INDEX = os.path.join(NOTES_DIR, "index.json")

def _ensure_dir():
    os.makedirs(NOTES_DIR, exist_ok=True)

def _load_index():
    _ensure_dir()
    if not os.path.exists(NOTES_INDEX):
        return {}
    try:
        with open(NOTES_INDEX, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def _save_index(idx):
    _ensure_dir()
    with open(NOTES_INDEX, "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2, ensure_ascii=False)

def _meta_path(filepath):
    return filepath.replace(".md", ".meta.json")

def _load_meta(filepath):
    mp = _meta_path(filepath)
    if not os.path.exists(mp):
        return {"pinned": False, "tags": [], "created": None, "updated": None}
    try:
        with open(mp, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"pinned": False, "tags": [], "created": None, "updated": None}

def _save_meta(filepath, meta):
    with open(_meta_path(filepath), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


class NotesModule(BaseModule):
    name = "Notas"
    icon = "📝"
    description = "Editor Markdown con buscador, tags y dashboard"

    def __init__(self, app):
        super().__init__(app)
        self.current_file = None
        self.autosave_job = None
        self._search_query = ""
        self._filter_tag = None

    def build(self, parent):
        self.content_frame = ctk.CTkFrame(parent, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=15, pady=15)
        main = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        main.pack(fill="both", expand=True)

        # ── SIDEBAR ────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(main, width=260, fg_color=self.colors["fg"], corner_radius=15)
        sidebar.pack(side="left", fill="y", padx=(0, 12))
        sidebar.pack_propagate(False)

        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 5))
        ctk.CTkLabel(header, text="📝 Notas", font=("Arial", 22, "bold"), text_color=self.colors["text"]).pack(side="left")
        ctk.CTkButton(header, text="+", width=35, command=self.create_note,
                      fg_color=self.colors["accent"], hover_color=self.colors["hover"]).pack(side="right")

        self.search_entry = ctk.CTkEntry(sidebar, placeholder_text="🔍 Buscar nota...", fg_color=self.colors["bg"])
        self.search_entry.pack(fill="x", padx=10, pady=(5, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_search())

        self.tag_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        self.tag_frame.pack(fill="x", padx=10, pady=(0, 5))
        self._rebuild_tag_bar()

        ctk.CTkButton(sidebar, text="🔄 Recargar", command=self._reload,
                      fg_color=self.colors["accent"], hover_color=self.colors["hover"]).pack(fill="x", padx=10, pady=(0, 5))

        self.files_frame = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        self.files_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ── EDITOR ─────────────────────────────────────────────────
        editor_container = ctk.CTkFrame(main, fg_color=self.colors["fg"], corner_radius=15)
        editor_container.pack(side="right", fill="both", expand=True)

        topbar = ctk.CTkFrame(editor_container, fg_color="transparent")
        topbar.pack(fill="x", padx=15, pady=(10, 5))

        self.file_label = ctk.CTkLabel(topbar, text="📝 Selecciona una nota", font=("Arial", 18, "bold"),
                                       text_color=self.colors["text"])
        self.file_label.pack(side="left")

        btn_row = ctk.CTkFrame(topbar, fg_color="transparent")
        btn_row.pack(side="right")

        self.pin_btn = ctk.CTkButton(btn_row, text="📌", width=35, command=self._toggle_pin,
                                     fg_color="transparent", hover_color=self.colors["hover"])
        self.pin_btn.pack(side="left", padx=2)

        ctk.CTkButton(btn_row, text="📤 Exportar", command=self._export_note,
                      fg_color="transparent", hover_color=self.colors["hover"],
                      text_color=self.colors["text_secondary"]).pack(side="left", padx=2)

        ctk.CTkButton(btn_row, text="🗑️", width=35, command=self._delete_note,
                      fg_color="transparent", hover_color="#c0392b",
                      text_color=self.colors["text_secondary"]).pack(side="left", padx=2)

        ctk.CTkButton(btn_row, text="💾 Guardar", command=self.save_current_file,
                      fg_color=self.colors["success"], hover_color=self.colors["hover"]).pack(side="left", padx=2)

        # ── Toolbar de formato ──────────────────────────────────────
        fmt_bar = ctk.CTkFrame(editor_container, fg_color="transparent", height=32)
        fmt_bar.pack(fill="x", padx=15, pady=(0, 2))

        fmt_actions = [
            ("B", "bold"), ("I", "italic"), ("H1", "h1"),
            ("H2", "h2"), ("•", "ul"), ("1.", "ol"), ("🔗", "link"),
        ]
        for label, action in fmt_actions:
            ctk.CTkButton(fmt_bar, text=label, width=36, height=26,
                          command=lambda a=action: self._insert_format(a),
                          fg_color=self.colors["bg"], hover_color=self.colors["hover"],
                          text_color=self.colors["text"]).pack(side="left", padx=1)

        # ── COPILOT (Llama 3) ───────────────────────────────────────
        sep = ctk.CTkFrame(fmt_bar, width=1, height=20, fg_color=self.colors["border"])
        sep.pack(side="left", padx=6)

        self.copilot_ollama_ok = getattr(self.app, "ollama", None) and self.app.ollama.available
        copilot_actions = [
            ("✨ Completar", "complete"),
            ("✓ Corregir", "correct"),
            ("🔄 Reescribir", "rewrite"),
            ("▶ Continuar", "continue"),
        ]
        for label, action in copilot_actions:
            ctk.CTkButton(fmt_bar, text=label, height=26,
                          command=lambda a=action: self._copilot_action(a),
                          fg_color=self.colors["accent"] if self.copilot_ollama_ok else self.colors["hover"],
                          hover_color=self.colors["hover"],
                          text_color=self.colors["text"],
                          font=("Arial", 10)).pack(side="left", padx=1)

        self.copilot_status = ctk.CTkLabel(fmt_bar, text="", font=("Arial", 9),
                                           text_color=self.colors["text_secondary"])
        self.copilot_status.pack(side="left", padx=6)

        # ── Textbox ─────────────────────────────────────────────────
        self.editor = ctk.CTkTextbox(editor_container, fg_color=self.colors["bg"],
                                     text_color=self.colors["text"], font=("Consolas", 14))
        self.editor.pack(fill="both", expand=True, padx=15, pady=(0, 5))
        self.editor.bind("<KeyRelease>", self.schedule_autosave)
        self.editor.bind("<Control-s>", lambda e: self.save_current_file())

        # ── Status bar ──────────────────────────────────────────────
        self.status_bar = ctk.CTkFrame(editor_container, fg_color="transparent", height=24)
        self.status_bar.pack(fill="x", padx=15, pady=(0, 10))
        self.status_label = ctk.CTkLabel(self.status_bar, text="", font=("Arial", 10),
                                         text_color=self.colors["text_secondary"])
        self.status_label.pack(side="left")
        self.save_label = ctk.CTkLabel(self.status_bar, text="✅", font=("Arial", 10),
                                      text_color=self.colors["success"])
        self.save_label.pack(side="right")

        _ensure_dir()
        self._reload()

    # ── TAG BAR ────────────────────────────────────────────────────
    def _rebuild_tag_bar(self):
        for w in self.tag_frame.winfo_children():
            w.destroy()
        all_tags = set()
        for fname in os.listdir(NOTES_DIR):
            if fname.endswith(".meta.json"):
                try:
                    with open(os.path.join(NOTES_DIR, fname), "r") as f:
                        meta = json.load(f)
                    all_tags.update(meta.get("tags", []))
                except json.JSONDecodeError:
                    logger.debug("Error parseando metadatos de nota: %s", fname)
        if not all_tags:
            ctk.CTkLabel(self.tag_frame, text="Sin etiquetas", font=("Arial", 9),
                        text_color=self.colors["text_secondary"]).pack(anchor="w")
            return
        row = ctk.CTkFrame(self.tag_frame, fg_color="transparent")
        row.pack(fill="x")
        def set_tag(t):
            self._filter_tag = t if self._filter_tag != t else None
            self._reload()
        ctk.CTkButton(row, text="✕", width=22, height=20, command=lambda: [setattr(self, '_filter_tag', None), self._reload()],
                      fg_color="transparent", text_color=self.colors["text_secondary"]).pack(side="left", padx=(0, 2))
        for tag in sorted(all_tags):
            active = tag == self._filter_tag
            ctk.CTkButton(row, text=f"#{tag}", height=20,
                         command=lambda t=tag: set_tag(t),
                         fg_color=self.colors["accent"] if active else self.colors["bg"],
                         text_color=self.colors["text"])
            tbtn = list(row.winfo_children())[-1]
            tbtn.pack(side="left", padx=1)

    # ── FILE LIST ──────────────────────────────────────────────────
    def _get_notes(self):
        _ensure_dir()
        notes = []
        idx = _load_index()
        for fname in os.listdir(NOTES_DIR):
            if not fname.endswith(".md"):
                continue
            path = os.path.join(NOTES_DIR, fname)
            meta = _load_meta(path)
            title = idx.get(fname, {}).get("title", fname.replace(".md", ""))
            notes.append({"name": fname, "path": path, "title": title, "meta": meta})
        return notes

    def _reload(self):
        self._rebuild_tag_bar()
        self._render_file_list()

    def _render_file_list(self):
        for w in self.files_frame.winfo_children():
            w.destroy()
        notes = self._get_notes()
        query = self.search_entry.get().lower().strip()
        if query:
            notes = [n for n in notes if query in n["title"].lower() or query in n["name"].lower()]
        if self._filter_tag:
            notes = [n for n in notes if self._filter_tag in n["meta"].get("tags", [])]
        notes.sort(key=lambda n: (not n["meta"].get("pinned", False), n["name"].lower()))

        if not notes:
            ctk.CTkLabel(self.files_frame, text="Sin resultados", text_color=self.colors["text_secondary"],
                         font=("Arial", 11)).pack(pady=20)
            return

        for n in notes:
            meta = n["meta"]
            pinned = meta.get("pinned", False)
            tags = meta.get("tags", [])
            label = f"{'📌 ' if pinned else '📄 '}{n['title']}"
            btn = ctk.CTkButton(self.files_frame, text=label, anchor="w",
                               fg_color=self.colors["bg"], hover_color=self.colors["hover"],
                               command=lambda p=n["path"]: self.open_markdown(p))
            btn.pack(fill="x", pady=2)

    def _on_search(self):
        self._render_file_list()

    # ── OPEN / SAVE ────────────────────────────────────────────────
    def open_markdown(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            self.current_file = filepath
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", content)
            meta = _load_meta(filepath)
            title = os.path.basename(filepath).replace(".md", "")
            self.file_label.configure(text=f"📝 {title}")
            self.pin_btn.configure(fg_color=self.colors["accent"] if meta.get("pinned") else "transparent")
            self._update_status()
        except Exception as e:
            self.app.toast.show(f"Error: {e}", type="error")

    def save_current_file(self):
        if not self.current_file:
            return
        try:
            content = self.editor.get("1.0", "end-1c")
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(content)
            idx = _load_index()
            fname = os.path.basename(self.current_file)
            idx[fname] = {"title": fname.replace(".md", ""), "updated": datetime.datetime.now().isoformat()}
            _save_index(idx)
            meta = _load_meta(self.current_file)
            meta["updated"] = datetime.datetime.now().isoformat()
            _save_meta(self.current_file, meta)
            self.save_label.configure(text="✅ Guardado")
            self.app.toast.show("Nota guardada", type="success", duration=1)
        except Exception as e:
            self.app.toast.show(str(e), type="error")

    def schedule_autosave(self, event=None):
        if self.autosave_job:
            self.content_frame.after_cancel(self.autosave_job)
        self.save_label.configure(text="⏳")
        self.autosave_job = self.content_frame.after(1500, self.save_current_file)
        self._update_status()

    def _update_status(self):
        if not self.current_file:
            self.status_label.configure(text="")
            return
        try:
            content = self.editor.get("1.0", "end-1c")
            words = len(content.split()) if content.strip() else 0
            chars = len(content)
            lines = content.count("\n") + 1
            meta = _load_meta(self.current_file)
            tags = ", ".join(meta.get("tags", [])) or "sin etiquetas"
            self.status_label.configure(text=f"{lines} líneas · {words} palabras · {chars} chars · #{tags}")
        except Exception:
            logger.debug("Error actualizando status de nota")

    # ── CREATE / DELETE ────────────────────────────────────────────
    def create_note(self):
        fname = f"nota_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        path = os.path.join(NOTES_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {fname.replace('.md','')}\n\n")
        now = datetime.datetime.now().isoformat()
        _save_meta(path, {"pinned": False, "tags": [], "created": now, "updated": now})
        idx = _load_index()
        idx[fname] = {"title": fname.replace(".md",""), "created": now}
        _save_index(idx)
        self._reload()
        self.open_markdown(path)
        self.app.toast.show("Nota creada", type="success")

    def _delete_note(self):
        if not self.current_file:
            return
        pop = ctk.CTkToplevel(self.app)
        pop.title("Eliminar nota")
        pop.geometry("320x140")
        pop.grab_set()
        ctk.CTkLabel(pop, text=f"¿Eliminar '{os.path.basename(self.current_file)}'?",
                    font=("Arial", 14, "bold"), text_color=self.colors["text"]).pack(pady=(20, 10))
        btn_row = ctk.CTkFrame(pop, fg_color="transparent")
        btn_row.pack()
        ctk.CTkButton(btn_row, text="Cancelar", command=pop.destroy,
                      fg_color=self.colors["hover"]).pack(side="left", padx=5)
        def do_delete():
            try:
                os.remove(self.current_file)
                mp = _meta_path(self.current_file)
                if os.path.exists(mp):
                    os.remove(mp)
                idx = _load_index()
                idx.pop(os.path.basename(self.current_file), None)
                _save_index(idx)
                self.current_file = None
                self.editor.delete("1.0", "end")
                self.file_label.configure(text="📝 Nota eliminada")
                self._reload()
                self.app.toast.show("Nota eliminada", type="success")
            except Exception as e:
                self.app.toast.show(f"Error: {e}", type="error")
            pop.destroy()
        ctk.CTkButton(btn_row, text="Eliminar", command=do_delete,
                      fg_color="#c0392b", hover_color="#e74c3c").pack(side="left", padx=5)

    # ── PIN / TAGS ─────────────────────────────────────────────────
    def _toggle_pin(self):
        if not self.current_file:
            return
        meta = _load_meta(self.current_file)
        meta["pinned"] = not meta.get("pinned", False)
        meta["updated"] = datetime.datetime.now().isoformat()
        _save_meta(self.current_file, meta)
        self.pin_btn.configure(fg_color=self.colors["accent"] if meta["pinned"] else "transparent")
        self._reload()

    def _set_tags(self, tags_str):
        if not self.current_file:
            return
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        meta = _load_meta(self.current_file)
        meta["tags"] = tags
        meta["updated"] = datetime.datetime.now().isoformat()
        _save_meta(self.current_file, meta)
        self._update_status()
        self._reload()

    # ── FORMAT TOOLBAR ─────────────────────────────────────────────
    def _insert_format(self, fmt):
        try:
            sel = self.editor.selection_get()
        except:
            sel = ""
        wrappers = {
            "bold": ("**", "**"),
            "italic": ("*", "*"),
            "h1": ("# ", ""),
            "h2": ("## ", ""),
            "ul": ("- ", ""),
            "ol": ("1. ", ""),
            "link": ("[", "](url)"),
        }
        if fmt in wrappers:
            left, right = wrappers[fmt]
            try:
                sel_start = self.editor.index("sel.first")
                sel_end = self.editor.index("sel.last")
                self.editor.delete(sel_start, sel_end)
                self.editor.insert(sel_start, f"{left}{sel}{right}")
            except:
                self.editor.insert("insert", f"{left}{sel}{right}")

    # ── COPILOT (Llama 3) ──────────────────────────────────────────
    def _copilot_action(self, action):
        if not self.copilot_ollama_ok:
            self.app.toast.show("Ollama no está disponible. Ejecuta 'ollama serve'", type="error")
            return
        if not self.current_file:
            self.app.toast.show("Abre una nota primero", type="info")
            return

        try:
            sel = self.editor.selection_get()
            sel_start = self.editor.index("sel.first")
            sel_end = self.editor.index("sel.last")
        except:
            sel = None
            sel_start = None
            sel_end = None

        if action in ("rewrite", "correct") and not sel:
            self.app.toast.show("Selecciona texto primero", type="info")
            return

        if action == "complete":
            cursor_pos = self.editor.index("insert")
            line_start = f"{cursor_pos.split('.')[0]}.0"
            text_before = self.editor.get(line_start, cursor_pos).strip()
            if not text_before:
                self.app.toast.show("Escribe algo primero", type="info")
                return
            prompt = f"Completa esta frase de forma natural en español (responde SOLO la continuación, sin repetir la frase):\n\n{text_before}"

        elif action == "correct":
            prompt = f"Corrige la gramática y ortografía de este texto en español. Responde SOLO el texto corregido, sin explicaciones:\n\n{sel}"

        elif action == "rewrite":
            prompt = f"Reescribe este texto en español con un tono más profesional y claro. Responde SOLO el texto reescrito:\n\n{sel}"

        elif action == "continue":
            content = self.editor.get("1.0", "end-1c").strip()
            if not content:
                self.app.toast.show("La nota está vacía", type="info")
                return
            last_lines = "\n".join(content.split("\n")[-5:])
            prompt = f"Continúa este texto en español de forma coherente. Responde SOLO la continuación directa, sin introducciones:\n\n{last_lines}"

        self.copilot_status.configure(text="🤖 Pensando...")
        threading.Thread(target=self._run_copilot, args=(action, prompt, sel_start, sel_end), daemon=True).start()

    def _run_copilot(self, action, prompt, sel_start, sel_end):
        try:
            result = self.app.ollama.generate(prompt, use_context=False, max_tokens=200)
            if not result or result.startswith("Error"):
                self.app.after(0, lambda: self.copilot_status.configure(text="⚠️ Error"))
                self.app.after(0, lambda: self.app.toast.show(result or "Sin respuesta", type="error"))
                return
            result = result.strip().strip('"').strip()

            def apply():
                if action in ("complete", "continue"):
                    self.editor.insert("insert", " " + result if action == "complete" else "\n" + result)
                elif action in ("correct", "rewrite") and sel_start:
                    self.editor.delete(sel_start, sel_end)
                    self.editor.insert(sel_start, result)
                self.copilot_status.configure(text="✅ Hecho")
                self.schedule_autosave()

            self.app.after(0, apply)
        except Exception as e:
            self.app.after(0, lambda: self.copilot_status.configure(text="⚠️ Error"))
            self.app.after(0, lambda: self.app.toast.show(str(e), type="error"))

    # ── EXPORT ─────────────────────────────────────────────────────
    def _export_note(self):
        if not self.current_file:
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Texto", "*.txt"), ("Todos", "*.*")],
            initialfile=os.path.basename(self.current_file)
        )
        if not path:
            return
        try:
            content = self.editor.get("1.0", "end-1c")
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.app.toast.show(f"Exportado a {os.path.basename(path)}", type="success")
        except Exception as e:
            self.app.toast.show(f"Error: {e}", type="error")

    # ── DASHBOARD WIDGET ───────────────────────────────────────────
    @classmethod
    def build_dashboard_widget(cls, app, parent):
        frame = ctk.CTkFrame(parent, fg_color=app.colors["fg"], corner_radius=15)
        frame.pack(fill="x", pady=(0, 12))

        hdr = ctk.CTkFrame(frame, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(10, 4))
        ctk.CTkLabel(hdr, text="📝 Notas Rápidas", font=("Arial", 13, "bold"),
                    text_color=app.colors["text"]).pack(side="left")

        notes_list = ctk.CTkScrollableFrame(frame, fg_color="transparent", height=140)
        notes_list.pack(fill="x", padx=10, pady=(0, 8))

        def refresh():
            for w in notes_list.winfo_children():
                w.destroy()
            notes = []
            _ensure_dir()
            for fname in os.listdir(NOTES_DIR):
                if not fname.endswith(".md"):
                    continue
                path = os.path.join(NOTES_DIR, fname)
                meta = _load_meta(path)
                notes.append({"name": fname, "path": path, "meta": meta})
            notes.sort(key=lambda n: (not n["meta"].get("pinned", False), n["meta"].get("updated", "")))
            notes = notes[:5]
            if not notes:
                ctk.CTkLabel(notes_list, text="Crea notas desde el módulo 📝",
                            text_color=app.colors["text_secondary"], font=("Arial", 10)).pack(pady=10)
                return
            for n in notes:
                row = ctk.CTkFrame(notes_list, fg_color=app.colors["bg"], corner_radius=6)
                row.pack(fill="x", pady=2)
                meta = n["meta"]
                label = f"{'📌 ' if meta.get('pinned') else '📄 '}{n['name'].replace('.md','')}"
                ctk.CTkLabel(row, text=label, font=("Arial", 10), text_color=app.colors["text"],
                            anchor="w").pack(side="left", padx=8, pady=4)
                def open_mod(path=n["path"]):
                    app._show_module_ui(app.modules.get("Notas"))
                    if hasattr(app.modules.get("Notas"), "open_markdown"):
                        app.modules["Notas"].open_markdown(path)
                ctk.CTkButton(row, text="📂", width=28, height=22, command=open_mod,
                             fg_color="transparent", hover_color=app.colors["hover"],
                             text_color=app.colors["text_secondary"]).pack(side="right", padx=4)

        refresh()
        ctk.CTkButton(frame, text="🔄", width=28, height=22, command=refresh,
                      fg_color="transparent", hover_color=app.colors["hover"],
                      text_color=app.colors["text_secondary"]).pack(anchor="e", padx=15, pady=(0, 6))

        return frame
