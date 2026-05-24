"""
Módulo Marketplace - Interfaz para descargar e instalar plugins
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
from typing import Optional

from .base_module import BaseModule
from .shared import ToolFrameContainer


class MarketplaceModule(BaseModule):
    """Módulo del Marketplace de Plugins para NetHUB"""

    name = "Marketplace"
    icon = "🏪"
    description = "Descarga e instala plugins de la comunidad"

    def __init__(self, app):
        super().__init__(app)
        self.marketplace = None
        self.current_search = ""
        self.plugin_frames = {}
        self.content_frame = None
        self.logger = None
        # NO inicializar marketplace aquí para evitar excepciones en __init__
        # Se inicializa lazy en build()

    def _init_marketplace(self):
        """Inicializa el gestor del marketplace (lazy)"""
        if self.marketplace is not None:
            return  # Ya inicializado
            
        try:
            from core.marketplace import MarketplaceManager
            
            plugins_dir = self.app.module_manager.get_plugins_dir()
            self.marketplace = MarketplaceManager(plugins_dir)
        except Exception as e:
            import traceback
            print(f"❌ Error inicializando marketplace: {e}")
            print(traceback.format_exc())
            self.marketplace = None

    def build(self, parent):
        """Construye la UI del marketplace"""
        # Inicializar marketplace si no lo está
        self._init_marketplace()
        
        colors = self.colors

        main_frame = ctk.CTkFrame(parent, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Header
        header = ctk.CTkFrame(main_frame, fg_color=colors["fg"], corner_radius=15)
        header.pack(fill="x", pady=(0, 20))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(fill="x", padx=20, pady=15)

        ctk.CTkLabel(
            title_frame,
            text=f"{self.icon} {self.name.upper()}",
            font=("Arial", 22, "bold"),
            text_color=colors["text"],
        ).pack(side="left")

        # Botón refrescar
        ctk.CTkButton(
            title_frame,
            text="🔄 Actualizar",
            command=self._refresh_catalog,
            fg_color=colors["accent"],
            hover_color=colors["hover"],
            width=120,
            height=30,
            font=("Arial", 11),
        ).pack(side="right", padx=(10, 0))

        # Search bar
        search_frame = ctk.CTkFrame(header, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            search_frame,
            text="Buscar:",
            font=("Arial", 12),
            text_color=colors["text_secondary"],
        ).pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Escribe para buscar plugins...",
            fg_color=colors["bg"],
            border_color=colors["accent"],
            text_color=colors["text"],
            height=35,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.search_entry.bind(
            "<KeyRelease>", lambda e: self._on_search_change(), after=True
        )

        ctk.CTkButton(
            search_frame,
            text="Buscar",
            command=self._on_search_change,
            fg_color=colors["accent"],
            hover_color=colors["hover"],
            width=100,
            height=35,
        ).pack(side="left")

        # Contenido - Scrollable
        scroll_frame = ctk.CTkScrollableFrame(
            main_frame, fg_color="transparent", scrollbar_button_color=colors["accent"]
        )
        scroll_frame.pack(fill="both", expand=True)

        self.content_frame = scroll_frame

        # Cargar catálogo
        if not self.marketplace:
            self._show_error("No se pudo inicializar el marketplace. Revisa la consola para más detalles.")
        else:
            self._load_plugins()

    def _load_plugins(self):
        """Carga y muestra los plugins del catálogo"""
        if not self.marketplace:
            self._show_error("No se pudo inicializar el marketplace")
            return

        # Limpiar
        for frame in self.plugin_frames.values():
            frame.destroy()
        self.plugin_frames.clear()

        plugins = self.marketplace.get_catalog()

        if not plugins:
            self._show_empty_state()
            return

        for plugin in plugins:
            self._create_plugin_card(plugin)

    def _create_plugin_card(self, plugin):
        """Crea una tarjeta para un plugin"""
        colors = self.colors
        plugin_id = plugin.get("id", "unknown")

        card = ctk.CTkFrame(self.content_frame, fg_color=colors["fg"], corner_radius=12)
        card.pack(fill="x", pady=8, padx=5)

        # Contenido de la tarjeta
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=15, pady=12)

        # Fila 1: Icon, Name, Version, Estatus
        header_row = ctk.CTkFrame(content, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 8))

        icon = plugin.get("icon", "📦")
        name = plugin.get("name", "Unknown")
        version = plugin.get("version", "?.?")

        ctk.CTkLabel(
            header_row,
            text=f"{icon} {name}",
            font=("Arial", 14, "bold"),
            text_color=colors["text"],
        ).pack(side="left")

        ctk.CTkLabel(
            header_row,
            text=f"v{version}",
            font=("Arial", 11),
            text_color=colors["text_secondary"],
        ).pack(side="left", padx=(10, 0))

        # Estatus
        if plugin.get("installed"):
            status_text = "✓ Instalado"
            status_color = "#00CC44"
        else:
            status_text = "● Disponible"
            status_color = colors["accent"]

        ctk.CTkLabel(
            header_row,
            text=status_text,
            font=("Arial", 10),
            text_color=status_color,
        ).pack(side="right")

        # Fila 2: Descripción
        desc = plugin.get("description", "Sin descripción")
        ctk.CTkLabel(
            content,
            text=desc,
            font=("Arial", 11),
            text_color=colors["text_secondary"],
            wraplength=600,
            justify="left",
        ).pack(fill="x", pady=(0, 8))

        # Fila 3: Autor, Tags, Botones
        footer = ctk.CTkFrame(content, fg_color="transparent")
        footer.pack(fill="x", pady=(8, 0))

        author = plugin.get("author", "Desconocido")
        ctk.CTkLabel(
            footer,
            text=f"👤 {author}",
            font=("Arial", 10),
            text_color=colors["text_secondary"],
        ).pack(side="left", padx=(0, 15))

        # Tags
        tags = plugin.get("tags", [])
        if tags:
            tags_text = ", ".join(tags[:3])  # Primeras 3 tags
            ctk.CTkLabel(
                footer,
                text=f"🏷️  {tags_text}",
                font=("Arial", 10),
                text_color=colors["text_secondary"],
            ).pack(side="left")

        # Botones
        button_frame = ctk.CTkFrame(footer, fg_color="transparent")
        button_frame.pack(side="right")

        if plugin.get("installed"):
            ctk.CTkButton(
                button_frame,
                text="Desinstalar",
                command=lambda pid=plugin_id: self._uninstall_plugin(pid),
                fg_color="#CC3333",
                hover_color="#AA2222",
                width=110,
                height=30,
                font=("Arial", 10),
            ).pack(side="left", padx=5)
        else:
            ctk.CTkButton(
                button_frame,
                text="Instalar",
                command=lambda pid=plugin_id: self._install_plugin(pid),
                fg_color=colors["accent"],
                hover_color=colors["hover"],
                width=110,
                height=30,
                font=("Arial", 10),
            ).pack(side="left", padx=5)

        # Ver detalles
        ctk.CTkButton(
            button_frame,
            text="Detalles",
            command=lambda pid=plugin_id: self._show_plugin_details(pid),
            fg_color=colors["bg"],
            border_color=colors["accent"],
            border_width=1,
            text_color=colors["accent"],
            width=110,
            height=30,
            font=("Arial", 10),
        ).pack(side="left", padx=5)

        self.plugin_frames[plugin_id] = card

    def _on_search_change(self):
        """Filtra plugins según la búsqueda"""
        if not self.marketplace:
            return

        query = self.search_entry.get().strip()
        self.current_search = query

        # Limpiar frames
        for frame in self.plugin_frames.values():
            frame.destroy()
        self.plugin_frames.clear()

        # Buscar
        if query:
            plugins = self.marketplace.search_plugins(query)
        else:
            plugins = self.marketplace.get_catalog()

        if not plugins:
            self._show_empty_state()
            return

        for plugin in plugins:
            self._create_plugin_card(plugin)

    def _install_plugin(self, plugin_id: str):
        """Instala un plugin con progreso"""
        if not self.marketplace:
            return

        # Crear ventana de progreso
        progress_window = ctk.CTkToplevel(self.app)
        progress_window.title("Instalando Plugin")
        progress_window.geometry("400x150")
        progress_window.resizable(False, False)

        colors = self.colors
        progress_window.configure(fg_color=colors["bg"])

        label = ctk.CTkLabel(
            progress_window,
            text=f"Instalando {plugin_id}...",
            font=("Arial", 12),
            text_color=colors["text"],
        )
        label.pack(pady=20)

        progress_bar = ctk.CTkProgressBar(
            progress_window,
            fg_color=colors["fg"],
            progress_color=colors["accent"],
        )
        progress_bar.pack(fill="x", padx=20, pady=10)
        progress_bar.set(0)

        status_label = ctk.CTkLabel(
            progress_window,
            text="Descargando...",
            font=("Arial", 10),
            text_color=colors["text_secondary"],
        )
        status_label.pack(pady=10)

        def progress_callback(message: str):
            status_label.configure(text=message)
            progress_bar.set(0.7)  # Progreso aproximado
            progress_window.update()

        def install_thread():
            success, message = self.marketplace.install_plugin(
                plugin_id, progress_callback
            )

            progress_window.destroy()

            if success:
                messagebox.showinfo("Éxito", message)
                self._load_plugins()
                if hasattr(self.app, "reload_modules"):
                    self.app.after(0, self.app.reload_modules)
            else:
                messagebox.showerror("Error", message)

        thread = threading.Thread(target=install_thread, daemon=True)
        thread.start()

    def _uninstall_plugin(self, plugin_id: str):
        """Desinstala un plugin"""
        if not self.marketplace:
            return

        if messagebox.askyesno(
            "Confirmar", f"¿Desinstalar {plugin_id}?"
        ):
            success, message = self.marketplace.uninstall_plugin(plugin_id)

            if success:
                messagebox.showinfo("Éxito", message)
                self._load_plugins()
            else:
                messagebox.showerror("Error", message)

    def _refresh_catalog(self):
        """Actualiza el catálogo desde GitHub"""
        if not self.marketplace:
            return

        # Mostrar progreso
        messagebox.showinfo("Actualizando", "Descargando catálogo...")

        def refresh_thread():
            success = self.marketplace.refresh_catalog()
            if success:
                self._load_plugins()
                messagebox.showinfo("Éxito", "Catálogo actualizado")
            else:
                messagebox.showwarning(
                    "Aviso", "No se pudo actualizar, usando caché local"
                )

        thread = threading.Thread(target=refresh_thread, daemon=True)
        thread.start()

    def _show_plugin_details(self, plugin_id: str):
        """Muestra detalles de un plugin en una ventana modal"""
        plugin = self.marketplace.get_plugin_details(plugin_id)
        if not plugin:
            return

        details_window = ctk.CTkToplevel(self.app)
        details_window.title(f"Detalles - {plugin.get('name', plugin_id)}")
        details_window.geometry("500x600")

        colors = self.colors
        details_window.configure(fg_color=colors["bg"])

        frame = ctk.CTkScrollableFrame(
            details_window, fg_color="transparent", scrollbar_button_color=colors["accent"]
        )
        frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Nombre
        ctk.CTkLabel(
            frame,
            text=plugin.get("name", "Unknown"),
            font=("Arial", 18, "bold"),
            text_color=colors["text"],
        ).pack(anchor="w", pady=(0, 5))

        # Versión y autor
        ctk.CTkLabel(
            frame,
            text=f"v{plugin.get('version', '?.?')} • {plugin.get('author', 'Unknown')}",
            font=("Arial", 11),
            text_color=colors["text_secondary"],
        ).pack(anchor="w", pady=(0, 15))

        # Descripción
        ctk.CTkLabel(
            frame,
            text="Descripción",
            font=("Arial", 12, "bold"),
            text_color=colors["text"],
        ).pack(anchor="w", pady=(15, 5))

        ctk.CTkLabel(
            frame,
            text=plugin.get("description", "Sin descripción"),
            font=("Arial", 11),
            text_color=colors["text_secondary"],
            wraplength=450,
            justify="left",
        ).pack(anchor="w", pady=(0, 15), fill="x")

        # Tags
        tags = plugin.get("tags", [])
        if tags:
            ctk.CTkLabel(
                frame,
                text="Categorías",
                font=("Arial", 12, "bold"),
                text_color=colors["text"],
            ).pack(anchor="w", pady=(15, 5))

            tags_text = ", ".join(tags)
            ctk.CTkLabel(
                frame,
                text=tags_text,
                font=("Arial", 11),
                text_color=colors["accent"],
            ).pack(anchor="w", pady=(0, 15))

        # Requisitos
        min_version = plugin.get("min_nethub_version", "2.0")
        ctk.CTkLabel(
            frame,
            text="Requisitos",
            font=("Arial", 12, "bold"),
            text_color=colors["text"],
        ).pack(anchor="w", pady=(15, 5))

        ctk.CTkLabel(
            frame,
            text=f"NetHUB mínimo: v{min_version}",
            font=("Arial", 11),
            text_color=colors["text_secondary"],
        ).pack(anchor="w", pady=(0, 15))

        # Licencia
        license_type = plugin.get("license", "No especificada")
        ctk.CTkLabel(
            frame,
            text="Licencia",
            font=("Arial", 12, "bold"),
            text_color=colors["text"],
        ).pack(anchor="w", pady=(15, 5))

        ctk.CTkLabel(
            frame,
            text=license_type,
            font=("Arial", 11),
            text_color=colors["text_secondary"],
        ).pack(anchor="w", pady=(0, 15))

        # Repository link
        repo = plugin.get("repository", "")
        if repo:
            def open_repo():
                import webbrowser
                webbrowser.open(repo)

            ctk.CTkButton(
                frame,
                text="🔗 Ver en GitHub",
                command=open_repo,
                fg_color=colors["accent"],
                hover_color=colors["hover"],
            ).pack(anchor="w", pady=(15, 0))

    def _show_empty_state(self):
        """Muestra estado vacío"""
        colors = self.colors

        empty_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        empty_frame.pack(fill="both", expand=True, padx=20, pady=50)

        ctk.CTkLabel(
            empty_frame,
            text="📭 Sin resultados",
            font=("Arial", 16, "bold"),
            text_color=colors["text_secondary"],
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            empty_frame,
            text="No se encontraron plugins que coincidan con tu búsqueda",
            font=("Arial", 12),
            text_color=colors["text_secondary"],
        ).pack()

    def _show_error(self, message: str):
        """Muestra un error"""
        colors = self.colors

        error_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        error_frame.pack(fill="both", expand=True, padx=20, pady=50)

        ctk.CTkLabel(
            error_frame,
            text="⚠️  Error",
            font=("Arial", 16, "bold"),
            text_color="#FF6666",
        ).pack(pady=(0, 10))

        ctk.CTkLabel(
            error_frame,
            text=message,
            font=("Arial", 12),
            text_color=colors["text_secondary"],
        ).pack()
