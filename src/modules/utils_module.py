import customtkinter as ctk
import os
import threading
import requests
import json

from .base_module import BaseModule
from .shared import ToolFrameContainer


class UtilsModule(BaseModule):
    name = "Aux Diagnostics"
    icon = "🔧"
    description = "Herramientas auxiliares y diagnósticos"

    def build(self, parent):
        self._build_tool_cards(parent, [
            ("Quick Notes", "Notas rápidas persistentes", self.notes, "📝"),
            ("Timer", "Cuenta regresiva táctil", self.timer_tool, "⏱️"),
        ])

    def notes(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Quick Notes", self.build, self.colors)
        win.pack(fill="both", expand=True)

        text = ctk.CTkTextbox(win, fg_color=self.colors["fg"], text_color=self.colors["text"])
        text.pack(fill="both", expand=True, padx=20, pady=10)

        notes_path = os.path.join(os.path.expanduser("~"), ".nethub_notes.txt")
        if os.path.exists(notes_path):
            try:
                with open(notes_path, "r", encoding="utf-8") as f:
                    text.insert("1.0", f.read())
            except:
                pass

        def save():
            try:
                content = text.get("1.0", "end-1c")
                with open(notes_path, "w", encoding="utf-8") as f:
                    f.write(content)
                app.toast.show("Notas guardadas", type="success")
            except:
                app.toast.show("Error al guardar", type="error")

        ctk.CTkButton(win, text="💾 Guardar", command=save, fg_color=self.colors["accent"]).pack(pady=10)

    def timer_tool(self):
        app = self.app
        app.clear_content()
        win = ToolFrameContainer(app.content_frame, "Timer", self.build, self.colors)
        win.pack(fill="both", expand=True)

        seconds_entry = ctk.CTkEntry(win, placeholder_text="Segundos", width=200)
        seconds_entry.pack(pady=20)
        timer_label = ctk.CTkLabel(win, text="", font=("Arial", 48), text_color=self.colors["accent"])
        timer_label.pack(pady=30)

        def countdown(remaining):
            if not win.winfo_exists() or not timer_label.winfo_exists():
                return
            if remaining >= 0:
                timer_label.configure(text=f"{remaining}s")
                app.after(1000, lambda: countdown(remaining - 1))
            else:
                timer_label.configure(text="¡Tiempo!")
                app.toast.show("Timer completado", type="success")

        def start():
            try:
                total = int(seconds_entry.get())
                countdown(total)
            except:
                app.toast.show("Ingresa un número válido", type="error")

        ctk.CTkButton(win, text="Iniciar", command=start, fg_color=self.colors["accent"]).pack()
