import customtkinter as ctk
import threading

from .base_module import BaseModule


class CodeModule(BaseModule):
    name = "Hex Code Sandbox"
    icon = "⚡"
    description = "Editor y sandbox de código Python"

    def build(self, parent):
        colors = self.colors
        app = self.app

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(frame, text="⚡ HEX PYTHON SCRIPT SANDBOX", font=("Arial", 20, "bold"),
                    text_color=colors["text"]).pack(pady=10)

        self.code_editor = ctk.CTkTextbox(frame, fg_color=colors["fg"], text_color=colors["text"], height=350)
        self.code_editor.pack(fill="both", expand=True, pady=10)
        self.code_editor.insert("1.0", "# Escribe tu código aquí\nimport psutil\nimport platform\n\nprint(f\"Sistema: {platform.system()}\")\nprint(f\"CPU: {psutil.cpu_percent()}%\")\nprint(f\"RAM: {psutil.virtual_memory().percent}%\")")

        ctk.CTkLabel(frame, text="Salida:", font=("Arial", 12), text_color=colors["text"]).pack(anchor="w")
        self.code_output = ctk.CTkTextbox(frame, fg_color=colors["fg"], text_color=colors["text"], height=150)
        self.code_output.pack(fill="x", pady=5)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)

        ctk.CTkButton(btn_frame, text="▶ Ejecutar", command=self.execute_code,
                     fg_color=colors["accent"], width=110).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🤖 Generar con IA", command=self.generate_code,
                     fg_color=colors["accent"], width=130).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🔍 Analizar con IA", command=self.explain_code,
                     fg_color=colors["accent_light"], width=130).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="🗑 Limpiar", command=lambda: self.code_output.delete("1.0", "end"),
                     fg_color=colors["fg"], width=90).pack(side="left", padx=5)

    def execute_code(self):
        app = self.app
        code = self.code_editor.get("1.0", "end-1c")
        self.code_output.delete("1.0", "end")
        result = app.ollama.execute_code(code)
        self.code_output.insert("1.0", result)
        app.toast.show("Código ejecutado", duration=1, type="success")

    def generate_code(self):
        app = self.app
        prompt = self.code_editor.get("1.0", "end-1c")
        if not prompt.strip():
            prompt = "un script que muestre información del sistema"

        app.toast.show("Generando código con IA...", type="info")

        def generate():
            response = app.ollama.generate(f"Genera solo el código Python para: {prompt}. No incluyas explicaciones. Usa print() para mostrar resultados.")
            app.after(0, lambda: hasattr(self, 'code_editor') and self.code_editor.winfo_exists() and (self.code_editor.delete("1.0", "end") or self.code_editor.insert("1.0", response)))
            app.after(0, lambda: app.toast.show("Código generado", type="success"))

        threading.Thread(target=generate, daemon=True).start()

    def explain_code(self):
        app = self.app
        code = self.code_editor.get("1.0", "end-1c")
        if not code.strip():
            app.toast.show("Escribe código para analizar", type="error")
            return

        self.code_output.delete("1.0", "end")
        self.code_output.insert("1.0", "🤖 Analizando tu código con la Inteligencia General de NetHUB...\n\n")
        app.toast.show("Analizando código con IA...", type="info")

        def run_analysis():
            prompt = f"Analiza detalladamente este código Python. Identifica posibles errores, problemas de rendimiento o vulnerabilidades de seguridad, explícalo brevemente y sugiere una versión optimizada:\n\n{code}"
            response = app.ollama.generate(prompt)
            app.after(0, lambda: self.code_output.winfo_exists() and (self.code_output.delete("1.0", "end") or self.code_output.insert("1.0", response)))
            app.after(0, lambda: app.toast.show("Análisis completado", type="success"))

        threading.Thread(target=run_analysis, daemon=True).start()
