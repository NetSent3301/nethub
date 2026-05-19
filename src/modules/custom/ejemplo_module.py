"""
PLANTILLA DE MODULO PERSONALIZADO PARA NETHUB
==============================================
Este archivo se cargara automaticamente al iniciar NetHUB.

Forma FACIL de crear un plugin:
  Settings → Modulos y Plugins → ✨ Nuevo plugin

Forma MANUAL:
  1. Crea una carpeta en plugins/ (junto al .exe o en la raiz del proyecto)
  2. Agrega plugin.json (nombre, icono, descripcion)
  3. Agrega main.py con tu clase que herede de BaseModule
  4. Settings → Recargar plugins
"""

import customtkinter as ctk

from ..base_module import BaseModule
from ..shared import ToolFrameContainer


class EjemploModule(BaseModule):
    """Modulo de ejemplo - puedes borrarlo o usarlo como plantilla."""

    name = "Ejemplo"
    icon = "🧪"
    description = "Modulo de ejemplo para demostrar como crear modulos custom"

    def build(self, parent):
        colors = self.colors

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=15)
        header.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header,
            text=f"{self.icon} {self.name.upper()}",
            font=("Arial", 22, "bold"),
            text_color=colors["text"],
        ).pack(pady=20, padx=20)

        info_box = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=12)
        info_box.pack(fill="x", pady=(0, 15))

        info_text = (
            "Este es un modulo personalizado.\n\n"
            "Para crear tu propio plugin:\n"
            "  1. Settings → Modulos y Plugins → ✨ Nuevo plugin\n"
            "  2. Escribe el nombre y se genera la plantilla\n"
            "  3. Edita plugins/<Nombre>/main.py\n"
            "  4. Click en 'Recargar plugins'\n\n"
            "Tambien puedes copiar este archivo a la carpeta\n"
            "custom/ si prefieres el metodo clasico.\n\n"
            f"Clase: {self.__class__.__name__}\n"
            f"Nombre: {self.name}\n"
            f"Icono: {self.icon}"
        )

        ctk.CTkLabel(
            info_box,
            text=info_text,
            font=("Arial", 12),
            text_color=colors["text_secondary"],
            justify="left",
        ).pack(pady=20, padx=20)

        ctk.CTkButton(
            frame,
            text="Hola desde el modulo custom",
            command=lambda: self.app.toast.show(
                f"Modulo '{self.name}' funcionando!", type="success"
            ),
            fg_color=colors["accent"],
            hover_color=colors["hover"],
            width=250,
            height=40,
        ).pack(pady=10)
