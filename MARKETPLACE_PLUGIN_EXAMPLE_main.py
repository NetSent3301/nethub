"""
Plugin de ejemplo: SSL Certificate Analyzer
Este archivo muestra cómo crear un plugin para NetHUB
"""

import customtkinter as ctk
from modules.base_module import BaseModule


class SSLAnalyzerModule(BaseModule):
    """Analizador de certificados SSL/TLS"""

    name = "SSL Analyzer"
    icon = "🔐"
    description = "Análisis de certificados SSL/TLS"

    def build(self, parent):
        """Construir interfaz del plugin"""
        colors = self.colors

        main_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        header.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header,
            text=f"{self.icon} {self.name}",
            font=("Arial", 20, "bold"),
            text_color=colors["text"],
        ).pack(pady=15)

        # Contenido
        content = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=12)
        content.pack(fill="both", expand=True)

        ctk.CTkLabel(
            content,
            text="Este es un plugin de ejemplo.\n\n"
            "Acciones disponibles:\n"
            "• Analizar certificado de un dominio\n"
            "• Verificar validez y fecha de expiración\n"
            "• Ver cadena de certificados\n"
            "• Validar HTTPS y TLS",
            font=("Arial", 12),
            text_color=colors["text_secondary"],
            justify="left",
        ).pack(padx=20, pady=20)

        # Inputs
        input_frame = ctk.CTkFrame(content, fg_color="transparent")
        input_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(
            input_frame,
            text="Dominio:",
            font=("Arial", 11),
            text_color=colors["text"],
        ).pack(side="left", padx=(0, 10))

        self.domain_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="ejemplo.com",
            fg_color=colors["bg"],
            border_color=colors["accent"],
            text_color=colors["text"],
        )
        self.domain_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            input_frame,
            text="Analizar",
            command=self._analyze,
            fg_color=colors["accent"],
            hover_color=colors["hover"],
        ).pack(side="left")

        # Resultados
        self.result_text = ctk.CTkTextbox(
            content,
            fg_color=colors["bg"],
            text_color=colors["text"],
            border_color=colors["accent"],
        )
        self.result_text.pack(fill="both", expand=True, padx=20, pady=10)
        self.result_text.configure(state="disabled")

    def _analyze(self):
        """Analizar certificado SSL"""
        domain = self.domain_entry.get().strip()

        if not domain:
            self._update_results("Por favor ingresa un dominio")
            return

        # Ejemplo: análisis simulado
        result = f"Analizando {domain}...\n\n"
        result += "Certificado SSL encontrado\n"
        result += "Estado: ✓ Válido\n"
        result += "Vencimiento: 2025-12-31\n"
        result += "Algoritmo: SHA-256\n"
        result += "Cadena: 3 certificados\n"

        self._update_results(result)

    def _update_results(self, text: str):
        """Actualizar área de resultados"""
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")
