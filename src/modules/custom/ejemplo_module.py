"""
PLANTILLA DE MODULO PERSONALIZADO PARA NETHUB
==============================================
Copia este archivo y modifica:
  1. El nombre de la clase (debe ser unico)
  2. Los atributos: name, icon, description
  3. El metodo build(parent) con tu logica

Este archivo se cargara automaticamente al iniciar NetHUB.
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
            "Para crear tu propio modulo:\n"
            "  1. Copia este archivo en modules/custom/\n"
            "  2. Cambia el nombre de la clase\n"
            "  3. Define name, icon y description\n"
            "  4. Implementa build(parent)\n\n"
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
