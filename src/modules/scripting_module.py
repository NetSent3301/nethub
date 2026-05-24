"""
NetHUB Script Console - Editor y explorador de API.
Permite ejecutar scripts, explorar comandos y ver eventos en vivo.
"""
import customtkinter as ctk
from .base_module import BaseModule
from core.logger import get_logger

logger = get_logger("scripting_module")


class ScriptingModule(BaseModule):
    name = "Script Console"
    icon = "\u2699"
    description = "Automatizacion y exploracion de API"

    api_commands = {
        "hello": lambda name="Mundo": f"Hola {name}!",
    }

    def build(self, parent):
        colors = self.colors
        app = self.app

        main = ctk.CTkFrame(parent, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Tabs ──────────────────────────────────────────────
        tabs = ctk.CTkTabview(main, fg_color=colors["fg"])
        tabs.pack(fill="both", expand=True)

        tab_console = tabs.add("Script")
        tab_api = tabs.add("API Explorer")
        tab_events = tabs.add("Event Monitor")

        self._build_console(tab_console, app, colors)
        self._build_api_explorer(tab_api, app, colors)
        self._build_event_monitor(tab_events, app, colors)

        app.events.subscribe("script.result", self._on_script_result, module="ScriptingModule")

    def _build_console(self, parent, app, colors):
        ctk.CTkLabel(
            parent,
            text="Escribe codigo Python. Usa 'api' para comandos y 'events' para eventos.",
            font=("Arial", 11),
            text_color=colors["text_secondary"],
        ).pack(anchor="w", padx=10, pady=(10, 5))

        editor_frame = ctk.CTkFrame(parent, fg_color=colors["fg"])
        editor_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.script_editor = ctk.CTkTextbox(
            editor_frame, fg_color=colors["bg"], text_color=colors["text"],
            font=("Consolas", 12), height=200
        )
        self.script_editor.pack(fill="both", expand=True, padx=5, pady=5)
        self.script_editor.insert("1.0", '# Ejemplo:\nresult = api.execute("system.toast", msg="Hola desde script!")\nprint(result)\n')

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(
            btn_frame, text="Ejecutar", command=self._run_script,
            fg_color=colors["accent"], hover_color=colors["hover"],
            width=120, height=35
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame, text="Limpiar output", command=self._clear_output,
            fg_color="#5a3a3a", hover_color="#7a4a4a",
            width=120, height=35
        ).pack(side="left", padx=5)

        self.script_output = ctk.CTkTextbox(
            parent, fg_color=colors["bg"], text_color="#8bc34a",
            font=("Consolas", 11), height=150
        )
        self.script_output.pack(fill="x", padx=10, pady=5)
        self.script_output.insert("1.0", "[output]\\n")

    def _build_api_explorer(self, parent, app, colors):
        ctk.CTkLabel(
            parent,
            text="Comandos disponibles en la API:",
            font=("Arial", 13, "bold"),
            text_color=colors["text"],
        ).pack(anchor="w", padx=15, pady=(15, 5))

        container = ctk.CTkFrame(parent, fg_color=colors["fg"])
        container.pack(fill="both", expand=True, padx=10, pady=5)

        canvas = ctk.CTkScrollableFrame(container, fg_color="transparent")
        canvas.pack(fill="both", expand=True)

        commands = app.api.list_commands()
        if not commands:
            ctk.CTkLabel(canvas, text="Sin comandos registrados",
                         text_color=colors["text_secondary"]).pack(pady=20)
            return

        for name, cmd in sorted(commands.items()):
            card = ctk.CTkFrame(canvas, fg_color=colors["bg"], corner_radius=8)
            card.pack(fill="x", padx=8, pady=3)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=6)

            ctk.CTkLabel(row, text=name, font=("Consolas", 12, "bold"),
                         text_color=colors["accent"]).pack(side="left")
            ctk.CTkLabel(row, text=f"[{cmd['module']}]", font=("Arial", 9),
                         text_color=colors["text_secondary"]).pack(side="left", padx=(8, 0))

            if cmd["description"]:
                ctk.CTkLabel(card, text=cmd["description"],
                             font=("Arial", 10), text_color=colors["text_secondary"],
                             anchor="w").pack(fill="x", padx=12, pady=(0, 6))

    def _build_event_monitor(self, parent, app, colors):
        ctk.CTkLabel(
            parent,
            text="Eventos del sistema en vivo:",
            font=("Arial", 13, "bold"),
            text_color=colors["text"],
        ).pack(anchor="w", padx=15, pady=(15, 5))

        self.event_log = ctk.CTkTextbox(
            parent, fg_color=colors["bg"], text_color=colors["text"],
            font=("Consolas", 11)
        )
        self.event_log.pack(fill="both", expand=True, padx=10, pady=5)
        self.event_log.insert("1.0", "[Esperando eventos...]\n")

        app.events.subscribe("*", self._on_any_event, module="ScriptingModule")

    def _on_any_event(self, event, **data):
        try:
            if not hasattr(self, "event_log") or not self.event_log.winfo_exists():
                return
            data_str = ", ".join(f"{k}={v}" for k, v in data.items() if k != "event")
            line = f"[{event}] {data_str}\n"
            self.event_log.insert("end", line)
            self.event_log.see("end")
            if int(self.event_log.index("end-1c").split(".")[0]) > 500:
                self.event_log.delete("1.0", "100.0")
        except Exception:
            logger.debug("Error en event monitor")

    def _on_script_result(self, event, **data):
        try:
            if hasattr(self, "script_output") and self.script_output.winfo_exists():
                status = "OK" if data.get("ok") else "ERROR"
                output = data.get("output", "")
                error = data.get("error", "")
                line = f"\n>>> {status}: {output}{error}\n"
                self.script_output.insert("end", line)
                self.script_output.see("end")
        except Exception:
            logger.debug("Error en script result handler")

    def _run_script(self):
        code = self.script_editor.get("1.0", "end-1c").strip()
        if not code:
            return
        result = self.app.scripts.run(code)
        self.app.events.emit("script.result", **result)
        if not result["ok"]:
            self.app.toast.show(f"Script error: {result['error'][:60]}", duration=4, type="error")

    def _clear_output(self):
        self.script_output.delete("1.0", "end")
        self.script_output.insert("1.0", "[output]\n")
