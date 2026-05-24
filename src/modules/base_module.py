import customtkinter as ctk


class BaseModule:
    """Plantilla base para crear nuevos módulos en NetHUB.

    Proporciona:
    - Eventos: subscribe_event, emit_event, event_map
    - API: api_commands (dict de comandos expuestos)
    - Ciclo de vida: on_activate, on_deactivate, on_api_registered
    """

    name = "Módulo sin nombre"
    icon = "📦"
    description = "Sin descripción"

    # Mapeo de eventos -> metodos: {"evento": "nombre_metodo"}
    event_map = {}

    # Comandos de API expuestos: {"nombre": funcion|dict}
    # Dict opcional: {"fn": func, "description": "...", "params": [...]}
    api_commands = {}

    def __init__(self, app):
        self.app = app
        self.colors = app.colors
        self.content_frame = None

    @property
    def menu_label(self):
        return f"{self.icon} {self.name}"

    def build(self, parent):
        raise NotImplementedError(
            f"El módulo {self.__class__.__name__} debe implementar build(parent)"
        )

    def _build_tool_cards(self, parent, tools):
        colors = self.colors
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20)

        header = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=10)
        header.pack(fill="x", pady=20)
        ctk.CTkLabel(
            header,
            text=f"{self.icon} {self.name.upper()}",
            font=("Arial", 22, "bold"),
            text_color=colors["text"],
        ).pack(pady=15)

        for title, desc, cmd, icon in tools:
            card = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=10)
            card.pack(fill="x", pady=6)

            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=14)

            ctk.CTkLabel(
                row, text=f"{icon}  {title}",
                font=("Arial", 15, "bold"),
                text_color=colors["text"],
            ).pack(side="left")

            ctk.CTkLabel(
                row, text=desc,
                font=("Arial", 11),
                text_color=colors["text_secondary"],
            ).pack(side="left", padx=(15, 0))

            ctk.CTkButton(
                row, text="Abrir", command=cmd,
                fg_color=colors["accent"], hover_color=colors["hover"],
                width=90, height=30,
            ).pack(side="right")

    def subscribe_event(self, event, callback=None):
        events = getattr(self.app, "events", None)
        if not events:
            return
        if callback:
            events.subscribe(event, callback, module=self.__class__.__name__)
        else:
            events.subscribe_module(self, {event: event.replace(".", "_")})

    def emit_event(self, event, **data):
        events = getattr(self.app, "events", None)
        if events:
            events.emit(event, **data)

    def emit_event_async(self, event, **data):
        events = getattr(self.app, "events", None)
        if events:
            events.emit_async(event, **data)

    def on_activate(self):
        pass

    def on_deactivate(self):
        pass

    def on_api_registered(self, api):
        pass
