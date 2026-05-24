"""
World Clock Plugin para NetHUB
Muestra la hora en diferentes zonas horarias del mundo
"""

import customtkinter as ctk
from datetime import datetime
import pytz
import threading
import time

from modules.base_module import BaseModule


class WorldClockModule(BaseModule):
    """Módulo Reloj Mundial - Muestra hora en diferentes zonas"""

    name = "World Clock"
    icon = "🌍"
    description = "Reloj mundial con múltiples zonas horarias"

    # Zonas horarias disponibles
    TIMEZONES = {
        "UTC": "UTC",
        "GMT": "GMT",
        "EST": "US/Eastern",
        "CST": "US/Central",
        "MST": "US/Mountain",
        "PST": "US/Pacific",
        "CET": "Europe/Paris",
        "EET": "Europe/Athens",
        "IST": "Asia/Kolkata",
        "JST": "Asia/Tokyo",
        "AEST": "Australia/Sydney",
        "NZST": "Pacific/Auckland",
    }

    def __init__(self, app):
        super().__init__(app)
        self.selected_zones = ["UTC", "EST", "CET", "IST", "JST"]
        self.clock_labels = {}
        self.running = False
        self.update_thread = None

    def build(self, parent):
        """Construir interfaz del reloj mundial"""
        colors = self.colors

        main_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        header.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header,
            text=f"{self.icon} {self.name}",
            font=("Arial", 22, "bold"),
            text_color=colors["text"],
        ).pack(pady=15)

        # Control de zonas horarias
        control_frame = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=12)
        control_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            control_frame,
            text="Selecciona zonas horarias:",
            font=("Arial", 12, "bold"),
            text_color=colors["text"],
        ).pack(pady=10)

        zones_grid = ctk.CTkFrame(control_frame, fg_color="transparent")
        zones_grid.pack(fill="x", padx=15, pady=(0, 10))

        self.zone_vars = {}
        for zone_name in self.TIMEZONES.keys():
            var = ctk.BooleanVar(value=zone_name in self.selected_zones)
            self.zone_vars[zone_name] = var

            checkbox = ctk.CTkCheckBox(
                zones_grid,
                text=zone_name,
                variable=var,
                command=self._on_zone_changed,
                fg_color=colors["accent"],
                checkmark_color=colors["bg"],
                text_color=colors["text"],
            )
            checkbox.pack(side="left", padx=5, pady=5)

        # Área de relojes
        self.clocks_frame = ctk.CTkScrollableFrame(
            main_frame,
            fg_color="transparent",
            scrollbar_button_color=colors["accent"],
        )
        self.clocks_frame.pack(fill="both", expand=True)

        # Iniciar actualización
        self.running = True
        self._update_clocks()
        self._start_clock_thread()

    def _on_zone_changed(self):
        """Actualizar zonas seleccionadas"""
        self.selected_zones = [
            zone for zone, var in self.zone_vars.items() if var.get()
        ]
        self._refresh_clocks()

    def _refresh_clocks(self):
        """Refresco de los relojes en pantalla"""
        # Limpiar labels anteriores
        for label in self.clock_labels.values():
            label.destroy()
        self.clock_labels.clear()

        # Recrear con zonas seleccionadas
        self._create_clock_displays()

    def _create_clock_displays(self):
        """Crear displays de reloj para cada zona"""
        colors = self.colors

        for zone_name in sorted(self.selected_zones):
            zone_frame = ctk.CTkFrame(
                self.clocks_frame, fg_color=colors["fg"], corner_radius=12
            )
            zone_frame.pack(fill="x", pady=8, padx=5)

            # Nombre de zona
            ctk.CTkLabel(
                zone_frame,
                text=f"{zone_name}",
                font=("Arial", 14, "bold"),
                text_color=colors["accent"],
            ).pack(anchor="w", padx=15, pady=(10, 5))

            # Hora (label que se actualizará)
            time_label = ctk.CTkLabel(
                zone_frame,
                text="--:--:--",
                font=("Arial", 32, "bold", "courier"),
                text_color=colors["text"],
            )
            time_label.pack(pady=(5, 10))

            # Ciudad/zona
            city_label = ctk.CTkLabel(
                zone_frame,
                text=self.TIMEZONES[zone_name],
                font=("Arial", 11),
                text_color=colors["text_secondary"],
            )
            city_label.pack(pady=(0, 10))

            self.clock_labels[zone_name] = time_label

    def _update_clocks(self):
        """Actualizar las horas en todos los relojes"""
        if not self.running:
            return

        now = datetime.now(pytz.UTC)

        for zone_name, time_label in self.clock_labels.items():
            tz = pytz.timezone(self.TIMEZONES[zone_name])
            local_time = now.astimezone(tz)
            time_str = local_time.strftime("%H:%M:%S")
            time_label.configure(text=time_str)

    def _start_clock_thread(self):
        """Thread para actualizar reloj cada segundo"""
        def clock_loop():
            while self.running:
                try:
                    self._update_clocks()
                    time.sleep(1)
                except Exception:
                    pass

        self.update_thread = threading.Thread(target=clock_loop, daemon=True)
        self.update_thread.start()

    def on_deactivate(self):
        """Limpieza cuando se desactiva el módulo"""
        self.running = False
