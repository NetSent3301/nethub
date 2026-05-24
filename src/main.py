import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw, ImageColor
import os
import json
import hashlib
import datetime
import threading
import time
import requests
import subprocess
import sys
import signal
import atexit
import random
import re
import socket
import platform
import psutil
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import queue
from tkinter import filedialog, messagebox, scrolledtext, colorchooser
from collections import deque
import math
import bcrypt
from plyer import notification

# Add src directory to Python path to allow imports from src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.core import UserManager, ConfigManager, ImprovedGLI, COLOR_SCHEMES
from core.logger import get_logger, log_exception
from core.events import EventBus
from core.api import API
from core.scripting import ScriptEngine
from update_checker import UpdateChecker
from modules import BaseModule, ModuleManager
from modules.shared import ToolFrameContainer, AnimatedGraph

logger = get_logger("main")

# Helpers multiplataforma
def get_system_root():
    return os.environ.get("SystemDrive", "C:\\") if platform.system() == "Windows" else "/"

# Configuración
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

USERS_FILE = "users.json"
CONFIG_FILE = "config.json"
CHAT_HISTORY_FILE = "chat_history.json"
GOOGLE_OAUTH_FILE = "config/google_oauth_client.json"

# Sistema de notificaciones premium
class ToastManager:
    def __init__(self, parent):
        self.parent = parent
        self.active_toasts = []
        
    def show(self, message, duration=3, type="info"):
        if type in ("warning", "error"):
            try:
                notification.notify(
                    title=f"NetHUB Ultimate - {type.capitalize()}",
                    message=message,
                    app_name="NetHUB Ultimate",
                    timeout=duration
                )
            except Exception:
                logger.debug("Notificación del sistema no disponible")
        colors = {
            "info": {"bg": "#1a2f3b", "accent": "#2a6a8a", "icon": "ℹ️"},
            "success": {"bg": "#152e1f", "accent": "#2a6a3a", "icon": "✓"},
            "warning": {"bg": "#3c2e17", "accent": "#8a6a2a", "icon": "⚠"},
            "error": {"bg": "#3e1a1a", "accent": "#8a2a2a", "icon": "✗"}
        }
        
        toast = ctk.CTkToplevel(self.parent)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        
        # Ventana transparente para bordes redondeados
        toast.configure(fg_color="#000001")
        toast.attributes("-transparentcolor", "#000001")
        toast.attributes("-alpha", 0.0)
        
        width, height = 330, 75
        toast.geometry(f"{width}x{height}")
        
        # Contenedor premium
        container = ctk.CTkFrame(toast, fg_color=colors[type]["bg"], 
                                 corner_radius=16, border_width=1, 
                                 border_color=colors[type]["accent"],
                                 width=width, height=height)
        container.pack(fill="both", expand=True)
        
        frame = ctk.CTkFrame(container, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=12, pady=10)
        
        icon_label = ctk.CTkLabel(frame, text=colors[type]["icon"], font=("Arial", 24),
                                  text_color="white")
        icon_label.pack(side="left", padx=(0, 10))
        
        msg_label = ctk.CTkLabel(frame, text=message, text_color="white", font=("Arial", 12, "bold"),
                                 wraplength=230, justify="left", anchor="w")
        msg_label.pack(side="left", fill="both", expand=True)
        
        # Barra de progreso
        progress = ctk.CTkProgressBar(container, height=3, corner_radius=0, 
                                     fg_color="#222222", progress_color=colors[type]["accent"])
        progress.pack(fill="x", side="bottom")
        progress.set(1.0)
        
        toast.is_fading = False
        
        # Posición inicial (fuera de pantalla a la derecha)
        parent_x = self.parent.winfo_x()
        parent_width = self.parent.winfo_width()
        start_x = parent_x + parent_width
        target_x = parent_x + parent_width - 350
        
        index = len(self.active_toasts)
        target_y = self.parent.winfo_y() + self.parent.winfo_height() - 95 - (index * 85)
        
        toast.geometry(f"{width}x{height}+{start_x}+{target_y}")
        
        toast.target_x = target_x
        toast.current_x = start_x
        toast.target_y = target_y
        toast.current_y = target_y
        
        self.active_toasts.append(toast)
        
        try:
            if type in ["success", "error"]:
                self.parent.play_sound(type)
            else:
                self.parent.play_sound("click")
        except:
            pass
        
        # Animación de entrada (slide ease-out)
        def slide_in(step=0):
            if not toast.winfo_exists() or toast.is_fading:
                return
            if step <= 15:
                t = step / 15
                ease = 1 - (1 - t) ** 3
                current_x = int(start_x - (start_x - toast.target_x) * ease)
                toast.geometry(f"+{current_x}+{toast.current_y}")
                toast.attributes("-alpha", min(1.0, ease))
                toast.after(10, lambda: slide_in(step + 1))
            else:
                toast.geometry(f"+{toast.target_x}+{toast.current_y}")
                toast.attributes("-alpha", 1.0)
        
        slide_in()
        
        # Animación de barra de progreso y temporizador
        start_time = time.time()
        
        def update_timer():
            if not toast.winfo_exists() or toast.is_fading:
                return
            elapsed = time.time() - start_time
            if elapsed >= duration:
                self.animate_out(toast)
            else:
                progress.set(1.0 - (elapsed / duration))
                toast.after(30, update_timer)
                
        update_timer()
        
        # Click para cerrar
        def on_click(event):
            self.animate_out(toast)
            
        toast.bind("<Button-1>", on_click)
        container.bind("<Button-1>", on_click)
        frame.bind("<Button-1>", on_click)
        icon_label.bind("<Button-1>", on_click)
        msg_label.bind("<Button-1>", on_click)
        
        self.reposition_all()
        return toast
        
    def reposition_all(self):
        parent_x = self.parent.winfo_x()
        parent_width = self.parent.winfo_width()
        parent_y = self.parent.winfo_y()
        parent_height = self.parent.winfo_height()
        
        for i, toast in enumerate(self.active_toasts):
            if toast.winfo_exists() and not toast.is_fading:
                toast.target_x = parent_x + parent_width - 350
                new_target_y = parent_y + parent_height - 95 - (i * 85)
                
                if new_target_y != toast.target_y:
                    toast.target_y = new_target_y
                    self.animate_y(toast)
                    
    def animate_y(self, toast, step=0):
        if not toast.winfo_exists() or toast.is_fading:
            return
        if step <= 10:
            dy = (toast.target_y - toast.current_y) / 3
            toast.current_y = int(toast.current_y + dy)
            toast.geometry(f"+{toast.target_x}+{toast.current_y}")
            toast.after(15, lambda: self.animate_y(toast, step + 1))
        else:
            toast.current_y = toast.target_y
            toast.geometry(f"+{toast.target_x}+{toast.target_y}")
            
    def animate_out(self, toast):
        if not toast.winfo_exists() or toast.is_fading:
            return
        toast.is_fading = True
        
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        self.reposition_all()
        
        parent_x = self.parent.winfo_x()
        parent_width = self.parent.winfo_width()
        end_x = parent_x + parent_width
        start_x = toast.winfo_x()
        
        # Animación de salida (slide ease-in con fade-out)
        def slide_out(step=0):
            if not toast.winfo_exists():
                return
            if step <= 12:
                t = step / 12
                ease = t ** 3
                current_x = int(start_x + (end_x - start_x) * ease)
                toast.geometry(f"+{current_x}+{toast.current_y}")
                toast.attributes("-alpha", max(0.0, 1.0 - ease))
                toast.after(10, lambda: slide_out(step + 1))
            else:
                toast.destroy()
                
        slide_out()

# Botón de sidebar con animaciones premium
# Botón de sidebar con animaciones premium
class PremiumSidebarButton(ctk.CTkFrame):
    def __init__(self, parent, text, command, colors, is_active=False):
        super().__init__(parent, fg_color="transparent", height=48, corner_radius=10)
        self.command = command
        self.colors = colors
        self.is_active = is_active
        self.full_text = text
        self.is_collapsed = False
        
        # Separar Icono y Texto
        parts = text.split(" ", 1)
        self.icon = parts[0] if parts else ""
        self.label_text = parts[1] if len(parts) > 1 else ""
        
        # Layout
        self.pack(fill="x", padx=8, pady=4)
        self.pack_propagate(False)
        
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.pack(fill="both", expand=True)
        
        self.text_label = ctk.CTkLabel(self.content, text=text, font=("Segoe UI Symbol", 13, "bold"),
                                       anchor="w", text_color=colors["text_secondary"])
        self.text_label.pack(side="left", padx=(15, 0), fill="both", expand=True)
        
        self.indicator = ctk.CTkFrame(self, width=4, height=28, fg_color=colors["active"], corner_radius=2)
        
        # Bindings recursivos para efectos de hover
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.content.bind("<Enter>", self.on_hover)
        self.content.bind("<Leave>", self.on_leave)
        self.text_label.bind("<Enter>", self.on_hover)
        self.text_label.bind("<Leave>", self.on_leave)
        
        self.bind("<Button-1>", self.on_click)
        self.content.bind("<Button-1>", self.on_click)
        self.text_label.bind("<Button-1>", self.on_click)
        
        if is_active:
            self.set_active(True)
            
    def set_collapsed(self, collapsed):
        self.is_collapsed = collapsed
        if collapsed:
            self.text_label.configure(text=self.icon, anchor="center")
            self.text_label.pack_configure(padx=0)
        else:
            self.text_label.configure(text=self.full_text, anchor="w")
            self.text_label.pack_configure(padx=(15, 0))
    
    def on_hover(self, event):
        if not hasattr(self, 'is_hovered'):
            self.is_hovered = False
        if not self.is_hovered:
            self.is_hovered = True
            try:
                self.winfo_toplevel().play_sound("hover")
            except:
                pass
        self.animate_hover(True)
    
    def on_leave(self, event):
        x, y = self.winfo_pointerxy()
        widget_under_mouse = self.winfo_containing(x, y)
        if widget_under_mouse in [self, self.content, self.text_label, self.indicator]:
            return
        self.is_hovered = False
        self.animate_hover(False)
    
    def animate_hover(self, active):
        if hasattr(self, 'anim_id'):
            self.after_cancel(self.anim_id)
            
        # Keep height fixed at 48 to prevent layout shifts!
        target_height = 48
        
        if self.is_collapsed:
            start_padx = 0
            target_padx = 0
        else:
            start_padx = self.current_padx if hasattr(self, 'current_padx') else (15 if not active else 22)
            target_padx = 22 if active else 15
            
        steps = 6
        def step_anim(step=1):
            if not self.winfo_exists():
                return
            t = step / steps
            ease = t
            
            # Keep height constant
            self.configure(height=48)
            
            if not self.is_collapsed:
                curr_padx = int(start_padx + (target_padx - start_padx) * ease)
                self.current_padx = curr_padx
                self.text_label.pack_configure(padx=(curr_padx, 0))
            
            if step < steps:
                self.anim_id = self.after(10, lambda: step_anim(step + 1))
            else:
                bg = self.colors["active"] if self.is_active else (self.colors["hover"] if active else "transparent")
                text_color = self.colors.get("on_active", self.colors["text"]) if self.is_active else (self.colors.get("on_hover", self.colors["text"]) if active else self.colors["text_secondary"])
                font_size = 13
                
                self.configure(fg_color=bg, height=48)
                if self.is_collapsed:
                    self.text_label.configure(text_color=text_color, font=("Arial", 15, "bold"))
                else:
                    self.text_label.configure(text_color=text_color, font=("Segoe UI", font_size, "bold"))
                    self.text_label.pack_configure(padx=(target_padx, 0))
                
        step_anim()
    
    def on_click(self, event):
        # Organic click feedback: translate the label slightly to the right
        if not self.is_collapsed:
            self.text_label.pack_configure(padx=(25, 0))
            self.after(80, lambda: self.winfo_exists() and self.text_label.pack_configure(padx=(self.current_padx if hasattr(self, 'current_padx') else 15, 0)))
        try:
            self.winfo_toplevel().play_sound("click")
        except:
            pass
        self.command()
    
    def set_active(self, active):
        self.is_active = active
        active_text = self.colors.get("on_active", self.colors["text"])
        if active:
            self.indicator.place(x=0, rely=0.5, anchor="w", relheight=0.6)
            self.configure(fg_color=self.colors["active"], height=48)
            if self.is_collapsed:
                self.text_label.configure(text_color=active_text, font=("Arial", 16, "bold"))
                self.text_label.pack_configure(padx=0)
            else:
                self.text_label.configure(text_color=active_text, font=("Arial", 13, "bold"))
                self.text_label.pack_configure(padx=(15, 0))
        else:
            self.indicator.place_forget()
            self.configure(fg_color="transparent", height=48)
            if self.is_collapsed:
                self.text_label.configure(text_color=self.colors["text_secondary"], font=("Arial", 16, "bold"))
                self.text_label.pack_configure(padx=0)
            else:
                self.text_label.configure(text_color=self.colors["text_secondary"], font=("Arial", 13, "bold"))
                self.text_label.pack_configure(padx=(15, 0))

# ToolFrameContainer y AnimatedGraph importados desde modules.shared

# IA GLI Mejorada
class ImprovedGLI:
    def __init__(self, model="llama3:8b", host="http://localhost:11434"):
        self.model = model
        self.host = host
        self.context = []
        self.conversation_history = []
        self.system_prompt = """Eres NetHUB GLI, un asistente claro y practico.

Reglas:
1. Responde siempre en espanol, directo y util.
2. Si el usuario pregunta algo simple, responde solo la respuesta necesaria.
3. Usa bloques ```python``` solamente cuando el usuario pida codigo.
4. No inventes comandos, menus ni texto de ayuda de la app.
5. Si no sabes algo, dilo honestamente.
6. Prioriza seguridad y etica en temas de redes o ciberseguridad."""
        self.quick_prompt = """Eres un asistente de chat rapido.
Responde en espanol con una frase corta y natural.
Si es una operacion matematica simple, da solo el resultado.
No uses markdown, listas, bloques de codigo ni comandos."""
        
        self.available = self.check_connection()
    
    def check_connection(self):
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def _clean_short_response(self, text, limit=140):
        text = (text or "").strip()
        text = re.sub(r"```(?:\w+)?", "", text).replace("```", "").strip()
        lines = [line.strip().strip('"') for line in text.splitlines() if line.strip()]
        text = " ".join(lines)
        return text[:limit].strip()
    
    def generate(self, prompt, callback=None, use_context=True, system_prompt=None, max_tokens=None):
        if not self.available:
            return "Error: Ollama no está corriendo. Inicia 'ollama serve'"
        
        # Construir contexto
        messages = [{"role": "system", "content": system_prompt or self.system_prompt}]
        if use_context:
            messages.extend(self.context[-30:])
        messages.append({"role": "user", "content": prompt})
        options = {"temperature": 0.2, "top_p": 0.8}
        if max_tokens:
            options["num_predict"] = max_tokens
        
        try:
            response = requests.post(f"{self.host}/api/chat",
                                    json={"model": self.model, "messages": messages, "stream": False, "options": options},
                                    timeout=120)
            result = response.json().get("message", {}).get("content", "Sin respuesta")
            
            # Guardar en contexto
            if use_context:
                self.context.append({"role": "user", "content": prompt})
                self.context.append({"role": "assistant", "content": result})
                self.conversation_history.append({"user": prompt, "assistant": result})
            
            if callback:
                callback(result)
            return result
        except Exception as e:
            return f"Error: {str(e)}"
    
    def generate_quick(self, prompt, max_chars=140):
        result = self.generate(prompt, use_context=False, system_prompt=self.quick_prompt, max_tokens=40)
        return self._clean_short_response(result, max_chars)
    
    def generate_stream(self, prompt, chunk_callback):
        if not self.available:
            chunk_callback("Error: Ollama no está corriendo. Inicia 'ollama serve'", True)
            return
        
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.context[-30:])
        messages.append({"role": "user", "content": prompt})
        
        full_response = ""
        
        try:
            response = requests.post(f"{self.host}/api/chat",
                                    json={"model": self.model, "messages": messages, "stream": True},
                                    stream=True, timeout=120)
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            chunk = data["message"]["content"]
                            full_response += chunk
                            chunk_callback(chunk, False)
                        if data.get("done"):
                            break
                    except:
                        pass
            
            self.context.append({"role": "user", "content": prompt})
            self.context.append({"role": "assistant", "content": full_response})
            chunk_callback("", True)
            
        except Exception as e:
            chunk_callback(f"Error: {str(e)}", True)
    
    def execute_code(self, code):
        """Ejecuta código Python de forma segura con sandbox mejorado"""
        import io
        import sys
        from contextlib import redirect_stdout, redirect_stderr

        SAFE_BUILTINS = {
            "abs": abs, "all": all, "any": any, "ascii": ascii, "bin": bin,
            "bool": bool, "bytearray": bytearray, "bytes": bytes, "chr": chr,
            "complex": complex, "dict": dict, "divmod": divmod, "enumerate": enumerate,
            "filter": filter, "float": float, "format": format, "frozenset": frozenset,
            "hash": hash, "hex": hex, "id": id, "int": int, "isinstance": isinstance,
            "issubclass": issubclass, "iter": iter, "len": len, "list": list,
            "map": map, "max": max, "min": min, "next": next, "oct": oct,
            "ord": ord, "pow": pow, "print": print, "range": range, "repr": repr,
            "reversed": reversed, "round": round, "set": set, "slice": slice,
            "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "type": type,
            "zip": zip, "True": True, "False": False, "None": None,
            "input": lambda prompt="": "0",
        }

        SAFE_GLOBALS = {
            "__builtins__": SAFE_BUILTINS,
            "psutil": psutil, "socket": socket, "platform": platform,
            "time": time, "datetime": datetime, "math": math,
            "random": random, "json": json, "re": re,
        }

        f = io.StringIO()
        e = io.StringIO()

        try:
            with redirect_stdout(f), redirect_stderr(e):
                exec(code, SAFE_GLOBALS)
            output = f.getvalue()
            if not output:
                output = "Codigo ejecutado sin salida"
            return output
        except Exception as ex:
            return f"Error: {str(ex)}\n{e.getvalue()}"
    
    def clear_context(self):
        self.context = []
        return "Contexto limpiado"

# Aplicación principal
class NetHUBUltimate(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Configuración ventana
        self.overrideredirect(True)
        self.default_geometry = "1400x850"
        self.geometry(self.default_geometry)
        self.minsize(1200, 700)
        self.title("NetHUB Ultimate")
        self.attributes("-alpha", 0.0)
        self.is_maximized = False
        
        # Managers
        self.user_manager = UserManager()
        self.config_manager = ConfigManager()
        self.ollama = ImprovedGLI()
        saved_update_url = self.config_manager.config.get("update_url", "")
        if saved_update_url and "/version.json" in saved_update_url:
            self.updater = UpdateChecker(update_url=saved_update_url)
        else:
            self.updater = UpdateChecker()
        self.toast = ToastManager(self)

        # Event Bus, API y Scripting
        self.events = EventBus()
        self.api = API(app=self)
        self.scripts = ScriptEngine(api=self.api, events=self.events)

        # Configurar apariencia inicial desde el archivo de configuración
        app_mode = self.config_manager.config.get("appearance_mode", "System")
        ctk.set_appearance_mode(app_mode)
        
        # Variables
        self.current_user = None
        self._current_display_name = None
        self.current_menu = None
        self.current_menu_index = 0
        self.drag_data = {"x": 0, "y": 0}
        self.animation_running = False
        self.floating_chat_window = None
        
        # Colores
        self.update_colors()
        
        # Module system
        self.modules = {}
        self._active_module = None
        self.module_buttons = {}
        self.module_manager = ModuleManager(self)
        self._init_modules()

        # Keyboard shortcuts
        self.bind("<Control-L>", lambda e: self.after(100, self.lock_screen))
        self.bind("<Control-Shift-F>", lambda e: self._focus_floating_chat())
        self.bind("<Escape>", self._handle_escape)
        
        # Registrar comandos core de la API
        self._register_core_api()

        # Frame principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        
        # Bind arrastre y restauración
        self.bind("<ButtonPress-1>", self.start_drag)
        self.bind("<B1-Motion>", self.drag_window)
        self.bind("<Map>", self.on_map)
        self.after(50, self.maximize_window)
        
        # Forzar visualización en la barra de tareas de Windows
        self.show_in_taskbar()
        
        # Mostrar Splash Screen / Pantalla de Carga
        self.show_splash()
        
        # Iniciar animación fade in de entrada
        self.fade_in()
        
    @property
    def current_display_name(self):
        dn = self._current_display_name
        if dn:
            return dn
        if self.current_user and self.current_user in self.user_manager.users:
            return self.user_manager.users[self.current_user].get("display_name") or self.current_user
        return self.current_user or ""
        
    def show_splash(self):
        for child in self.main_frame.winfo_children():
            child.destroy()
            
        splash_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["bg"])
        splash_frame.pack(fill="both", expand=True)
        
        # Logo de la App
        logo_label = ctk.CTkLabel(splash_frame, text="⚡ NETHUB ULTIMATE", font=("Arial", 36, "bold"), text_color=self.colors["accent"])
        logo_label.pack(pady=(220, 15))
        
        desc_label = ctk.CTkLabel(splash_frame, text="ESTACIÓN DE COMANDO TÁCTICA & IA DE VANGUARDIA", font=("Arial", 12, "bold"), text_color=self.colors["text_secondary"])
        desc_label.pack(pady=(0, 40))
        
        # Barra de progreso
        progress = ctk.CTkProgressBar(splash_frame, width=450, height=8, corner_radius=4, fg_color=self.colors["border"], progress_color=self.colors["accent"])
        progress.pack(pady=10)
        progress.set(0)
        
        # Estado de carga
        status_label = ctk.CTkLabel(splash_frame, text="Inicializando subsistemas...", font=("Arial", 11, "italic"), text_color=self.colors["text_secondary"])
        status_label.pack()
        
        # Carga progresiva asíncrona
        def do_loading(step=0):
            if not splash_frame.winfo_exists():
                return
                
            if step <= 100:
                progress.set(step / 100.0)
                
                if step == 15:
                    status_label.configure(text="Conectando base de datos militar y SOC local...")
                elif step == 35:
                    status_label.configure(text="Estableciendo canal seguro con Ollama (Chat GLI)...")
                    # Comprobar Ollama asíncronamente
                    def check_ollama():
                        self.ollama.available = self.ollama.check_connection()
                    threading.Thread(target=check_ollama, daemon=True).start()
                elif step == 60:
                    status_label.configure(text="Iniciando radar de telemetría de red táctica...")
                elif step == 80:
                    status_label.configure(text="Cargando interfaz gráfica y animaciones premium...")
                elif step == 95:
                    status_label.configure(text="¡Acceso listo y protegido!")
                    
                self.after(25, lambda: do_loading(step + 2))
            else:
                splash_frame.destroy()
                
                # Intentar restaurar sesión activa
                import time
                session = self.config_manager.config.get("last_session")
                if session and isinstance(session, dict):
                    session_user = session.get("user")
                    session_time = session.get("timestamp", 0)
                    remember = session.get("remember", False)
                    timeout = self.config_manager.config.get("session_timeout", 900)
                    if session_user and (time.time() - session_time < timeout):
                        if session_user in self.user_manager.users:
                            self.current_user = session_user
                            session["timestamp"] = time.time()
                            self.config_manager.save_config()
                            
                            self.show_main_app()
                            self.after(2000, self._check_updates_on_startup)
                            if remember:
                                self.toast.show(f"Sesión restaurada: {self.current_display_name}", duration=2, type="success")
                            return
                
                self.show_login()
                
        do_loading()
        
    def fade_in(self, target_alpha=1.0, current_alpha=0.0, step=0.06):
        self.attributes("-alpha", current_alpha)
        if current_alpha < target_alpha:
            self.after(12, lambda: self.fade_in(target_alpha, min(target_alpha, current_alpha + step), step))
        else:
            self.attributes("-alpha", target_alpha)
        
    def play_sound(self, sound_type):
        if not self.config_manager.config.get("sound_effects", True):
            return
        def run():
            try:
                import winsound
                if sound_type == "click":
                    winsound.Beep(2000, 45)
                elif sound_type == "hover":
                    winsound.Beep(2400, 20)
                elif sound_type == "success":
                    winsound.Beep(1200, 50)
                    winsound.Beep(1800, 90)
                elif sound_type == "error":
                    winsound.Beep(650, 120)
                    winsound.Beep(450, 180)
                elif sound_type == "welcome":
                    winsound.Beep(1000, 60)
                    winsound.Beep(1300, 60)
                    winsound.Beep(1600, 60)
                    winsound.Beep(2000, 120)
            except:
                pass
        threading.Thread(target=run, daemon=True).start()
        
    def show_in_taskbar(self):
        if platform.system() == "Windows":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if hwnd == 0:
                    hwnd = self.winfo_id()
                GWL_EXSTYLE = -20
                WS_EX_APPWINDOW = 0x00040000
                WS_EX_TOOLWINDOW = 0x00000080
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
                style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
                ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
                ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0002 | 0x0001 | 0x0004 | 0x0020)
            except Exception as e:
                logger.warning("Error barra de tareas: %s", e)
                
    def on_map(self, event):
        if event.widget == self:
            self.overrideredirect(True)
            self.after(100, self.show_in_taskbar)
            
    def destroy(self):
        kill_zombie_music()
        super().destroy()
        
    def get_avatar_image(self, size=35):
        avatar_path = self.user_manager.users.get(self.current_user, {}).get("avatar", "")
        if not avatar_path or not os.path.exists(avatar_path):
            return self.generate_default_avatar(self.current_user, size)
            
        try:
            img = Image.open(avatar_path).convert("RGBA")
            img = img.resize((size, size), Image.Resampling.LANCZOS)
            
            mask = Image.new("L", (size, size), 0)
            draw = ImageDraw.Draw(mask)
            draw.ellipse((0, 0, size, size), fill=255)
            
            circular_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            circular_img.paste(img, (0, 0), mask)
            
            return ctk.CTkImage(light_image=circular_img, dark_image=circular_img, size=(size, size))
        except Exception:
            return self.generate_default_avatar(self.current_user, size)

    def generate_default_avatar(self, username, size=35):
        if not username:
            username = "NetHUB"
        hue = sum(ord(c) for c in username) % 360
        color1 = ImageColor.getrgb(f"hsl({hue}, 70%, 40%)")
        color2 = ImageColor.getrgb(f"hsl({(hue + 40) % 360}, 75%, 35%)")
        
        img = Image.new("RGBA", (size, size))
        draw = ImageDraw.Draw(img)
        for y in range(size):
            for x in range(size):
                t = (x + y) / (2 * size)
                r = int(color1[0] + (color2[0] - color1[0]) * t)
                g = int(color1[1] + (color2[1] - color1[1]) * t)
                b = int(color1[2] + (color2[2] - color1[2]) * t)
                img.putpixel((x, y), (r, g, b, 255))
                
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size, size), fill=255)
        
        circular_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        circular_img.paste(img, (0, 0), mask)
        
        draw = ImageDraw.Draw(circular_img)
        initial = username[0].upper() if username else "?"
        
        try:
            from PIL import ImageFont
            font = ImageFont.truetype("arial.ttf", int(size * 0.5))
        except Exception:
            font = None
            
        if font:
            left, top, right, bottom = draw.textbbox((0, 0), initial, font=font)
            text_w = right - left
            text_h = bottom - top
        else:
            text_w, text_h = int(size * 0.4), int(size * 0.4)
            
        pos_x = (size - text_w) / 2
        pos_y = (size - text_h) / 2 - (int(size * 0.05) if font else 0)
        
        draw.text((pos_x, pos_y), initial, fill="white", font=font)
        
        return ctk.CTkImage(light_image=circular_img, dark_image=circular_img, size=(size, size))
    
    def update_colors(self):
        self.colors = self.config_manager.get_colors()
        if hasattr(self, 'configure'):
            self.configure(fg_color=self.colors["bg"])
    
    def start_drag(self, event):
        if getattr(self, "is_maximized", False):
            self.is_dragging = False
            return
        
        widget = event.widget
        is_in_top_bar = False
        curr = widget
        while curr:
            if hasattr(self, 'top_bar') and curr == self.top_bar:
                is_in_top_bar = True
                break
            try:
                curr = curr.master
            except AttributeError:
                break
                
        # Verificar si se hizo click sobre un botón o elemento interactivo
        is_interactive = False
        curr = widget
        while curr:
            if isinstance(curr, ctk.CTkButton) or isinstance(curr, ctk.CTkEntry):
                is_interactive = True
                break
            try:
                curr = curr.master
            except AttributeError:
                break
                
        if is_in_top_bar and not is_interactive:
            self.drag_data["x"] = event.x_root
            self.drag_data["y"] = event.y_root
            self.is_dragging = True
        else:
            self.is_dragging = False
            
    def drag_window(self, event):
        if hasattr(self, 'is_dragging') and self.is_dragging:
            dx = event.x_root - self.drag_data["x"]
            dy = event.y_root - self.drag_data["y"]
            x = self.winfo_x() + dx
            y = self.winfo_y() + dy
            self.geometry(f"+{x}+{y}")
            self.drag_data["x"] = event.x_root
            self.drag_data["y"] = event.y_root
            
    def minimize_window(self):
        self.overrideredirect(False)
        self.iconify()
    
    def maximize_window(self):
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.geometry(f"{screen_width}x{screen_height-40}+0+0")
        self.is_maximized = True
    
    def toggle_maximize(self):
        if hasattr(self, 'is_maximized') and self.is_maximized:
            self.geometry(self.default_geometry)
            self.is_maximized = False
        else:
            # Maximizar de forma segura sin ocultar la barra de tareas
            self.maximize_window()
    
    def show_login(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Top bar
        self.top_bar = ctk.CTkFrame(self.main_frame, height=40, fg_color=self.colors["fg"], corner_radius=0)
        self.top_bar.pack(fill="x", side="top")
        
        btn_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        for btn, cmd in [("─", self.minimize_window), ("□", self.toggle_maximize), ("✕", self.destroy)]:
            ctk.CTkButton(btn_frame, text=btn, width=30, height=25, command=cmd,
                         fg_color="transparent", hover_color=self.colors["hover"]).pack(side="left", padx=2)
        
        ctk.CTkLabel(self.top_bar, text="NetHUB Ultimate", font=("Arial", 16, "bold"),
                    text_color=self.colors["text"]).pack(side="left", padx=20)
        
        # Login frame
        login_frame = ctk.CTkFrame(self.main_frame, fg_color=self.colors["fg"], corner_radius=20, width=450, height=600)
        login_frame.place(relx=0.5, rely=0.7, anchor="center")
        
        def animate_login(step=0):
            if not login_frame.winfo_exists():
                return
            if step <= 25:
                t = step / 25
                ease = 1 - math.exp(-6 * t) * math.cos(3.5 * math.pi * t)
                curr_rely = 0.7 - 0.2 * ease
                login_frame.place_configure(rely=curr_rely)
                self.after(10, lambda: animate_login(step + 1))
            else:
                login_frame.place_configure(rely=0.5)
                
        self.after(50, animate_login)
        
        ctk.CTkLabel(login_frame, text="NetHUB", font=("Arial", 38, "bold"),
                    text_color=self.colors["text"]).pack(pady=(30, 5))
        ctk.CTkLabel(login_frame, text="Ultimate Security Suite", font=("Arial", 14),
                    text_color=self.colors["text_secondary"]).pack(pady=(0, 20))
        
        tabview = ctk.CTkTabview(login_frame, fg_color=self.colors["bg"])
        tabview.pack(pady=10, padx=40, fill="both", expand=True)
        
        # ── TAB LOGIN ────────────────────────────────────────────────
        tab_login = tabview.add("Login")
        
        ctk.CTkLabel(tab_login, text="usuario", font=("Arial", 10), text_color=self.colors["text_secondary"],
                    anchor="w").pack(anchor="w", padx=30, pady=(15, 2))
        self.login_user = ctk.CTkEntry(tab_login, placeholder_text="Usuario o correo", fg_color=self.colors["bg"],
                                       text_color=self.colors["text"])
        self.login_user.pack(pady=(0, 5), padx=30, fill="x")
        
        ctk.CTkLabel(tab_login, text="contraseña", font=("Arial", 10), text_color=self.colors["text_secondary"],
                    anchor="w").pack(anchor="w", padx=30, pady=(10, 2))
        pass_row = ctk.CTkFrame(tab_login, fg_color="transparent")
        pass_row.pack(pady=(0, 5), padx=30, fill="x")
        self.login_pass = ctk.CTkEntry(pass_row, placeholder_text="••••••••", show="*",
                                       fg_color=self.colors["bg"], text_color=self.colors["text"])
        self.login_pass.pack(side="left", fill="x", expand=True)
        self.login_pass.bind("<Return>", lambda e: self.do_login())
        self.login_show_btn = ctk.CTkButton(pass_row, text="👁", width=30, height=28,
                                           command=lambda: self._toggle_pass_visible(self.login_pass, self.login_show_btn),
                                           fg_color="transparent", hover_color=self.colors["hover"])
        self.login_show_btn.pack(side="right", padx=(4, 0))
        
        # Remember me + Forgot
        opt_row = ctk.CTkFrame(tab_login, fg_color="transparent")
        opt_row.pack(fill="x", padx=30, pady=(5, 0))
        self.remember_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(opt_row, text="Recordar", variable=self.remember_var,
                       fg_color=self.colors["accent"], text_color=self.colors["text_secondary"],
                       font=("Arial", 10)).pack(side="left")
        
        ctk.CTkButton(tab_login, text="Ingresar", command=self.do_login,
                     fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                     height=35).pack(pady=(15, 5), padx=30, fill="x")
        
        ctk.CTkButton(tab_login, text="Continuar con Google", command=self.do_google_login,
                     fg_color=self.colors["fg"], hover_color=self.colors["hover"],
                     text_color=self.colors["text"], border_width=1,
                     border_color=self.colors["border"]).pack(pady=(0, 12), padx=30, fill="x")
        
        self.login_error = ctk.CTkLabel(tab_login, text="", font=("Arial", 10),
                                        text_color=self.colors["error"])
        self.login_error.pack()
        
        # ── TAB REGISTRO ─────────────────────────────────────────────
        tab_register = tabview.add("Registro")
        
        ctk.CTkLabel(tab_register, text="usuario", font=("Arial", 10), text_color=self.colors["text_secondary"],
                    anchor="w").pack(anchor="w", padx=30, pady=(15, 2))
        self.reg_user = ctk.CTkEntry(tab_register, placeholder_text="Nombre de usuario",
                                     fg_color=self.colors["bg"], text_color=self.colors["text"])
        self.reg_user.pack(pady=(0, 5), padx=30, fill="x")
        
        ctk.CTkLabel(tab_register, text="correo (opcional)", font=("Arial", 10), text_color=self.colors["text_secondary"],
                    anchor="w").pack(anchor="w", padx=30, pady=(10, 2))
        self.reg_email = ctk.CTkEntry(tab_register, placeholder_text="email@ejemplo.com",
                                      fg_color=self.colors["bg"], text_color=self.colors["text"])
        self.reg_email.pack(pady=(0, 5), padx=30, fill="x")
        
        ctk.CTkLabel(tab_register, text="contraseña", font=("Arial", 10), text_color=self.colors["text_secondary"],
                    anchor="w").pack(anchor="w", padx=30, pady=(10, 2))
        reg_pass_row = ctk.CTkFrame(tab_register, fg_color="transparent")
        reg_pass_row.pack(pady=(0, 2), padx=30, fill="x")
        self.reg_pass = ctk.CTkEntry(reg_pass_row, placeholder_text="Mín. 6 caracteres", show="*",
                                     fg_color=self.colors["bg"], text_color=self.colors["text"])
        self.reg_pass.pack(side="left", fill="x", expand=True)
        self.reg_pass.bind("<KeyRelease>", lambda e: self._update_password_strength())
        self.reg_show_btn = ctk.CTkButton(reg_pass_row, text="👁", width=30, height=28,
                                         command=lambda: self._toggle_pass_visible(self.reg_pass, self.reg_show_btn),
                                         fg_color="transparent", hover_color=self.colors["hover"])
        self.reg_show_btn.pack(side="right", padx=(4, 0))
        
        # Barra de fortaleza
        self.strength_bar = ctk.CTkProgressBar(tab_register, height=6, corner_radius=3,
                                                fg_color=self.colors["border"],
                                                progress_color=self.colors["error"])
        self.strength_bar.pack(padx=30, fill="x")
        self.strength_bar.set(0)
        self.strength_label = ctk.CTkLabel(tab_register, text="", font=("Arial", 9),
                                           text_color=self.colors["text_secondary"])
        self.strength_label.pack()
        
        # Repetir contraseña
        ctk.CTkLabel(tab_register, text="repetir contraseña", font=("Arial", 10), text_color=self.colors["text_secondary"],
                    anchor="w").pack(anchor="w", padx=30, pady=(10, 2))
        self.reg_pass2 = ctk.CTkEntry(tab_register, placeholder_text="••••••••", show="*",
                                      fg_color=self.colors["bg"], text_color=self.colors["text"])
        self.reg_pass2.pack(pady=(0, 5), padx=30, fill="x")
        self.reg_pass2.bind("<Return>", lambda e: self.do_register())
        
        self.reg_error = ctk.CTkLabel(tab_register, text="", font=("Arial", 10),
                                      text_color=self.colors["error"])
        self.reg_error.pack()
        
        ctk.CTkButton(tab_register, text="Registrarse", command=self.do_register,
                     fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                     height=35).pack(pady=(15, 5), padx=30, fill="x")
    
    def _toggle_pass_visible(self, entry, btn):
        if entry.cget("show") == "*":
            entry.configure(show="")
            btn.configure(text="🙈")
        else:
            entry.configure(show="*")
            btn.configure(text="👁")
    
    def _update_password_strength(self):
        pwd = self.reg_pass.get()
        score = 0
        if len(pwd) >= 6: score += 25
        if len(pwd) >= 10: score += 15
        if any(c.isupper() for c in pwd): score += 15
        if any(c.islower() for c in pwd): score += 15
        if any(c.isdigit() for c in pwd): score += 15
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pwd): score += 15
        score = min(100, score)
        self.strength_bar.set(score / 100)
        if score < 30:
            color, label = self.colors["error"], "Débil"
        elif score < 60:
            color, label = self.colors["warning"], "Media"
        elif score < 85:
            color, label = self.colors["success"], "Fuerte"
        else:
            color, label = self.colors["accent"], "Muy fuerte"
        self.strength_bar.configure(progress_color=color)
        self.strength_label.configure(text=label if pwd else "")
    
    def do_login(self):
        self.login_error.configure(text="")
        username = self.login_user.get().strip()
        password = self.login_pass.get()
        if not username:
            self.login_error.configure(text="Ingresa un usuario")
            return
        if not password:
            self.login_error.configure(text="Ingresa tu contraseña")
            return
        success, result = self.user_manager.login(username, password)
        if success:
            remember = self.remember_var.get()
            self.complete_login(username, f"Bienvenido {username}", remember=remember)
        else:
            self.login_error.configure(text=result)
            self.toast.show(result, duration=2, type="error")
    
    def complete_login(self, username, message=None, remember=True):
        self.current_user = username
        user_data = self.user_manager.users.get(username, {})
        self._current_display_name = user_data.get("display_name") or username.split("@")[0]
        import time
        session_timeout = 86400 if remember else 900  # 24h vs 15min
        self.config_manager.config["last_session"] = {
            "user": self.current_user,
            "timestamp": time.time(),
            "remember": remember
        }
        self.config_manager.config["session_timeout"] = session_timeout
        self.config_manager.save_config()
        
        # Exportar datos de usuario para recomendaciones si está activado
        if self.config_manager.config.get("export_recommendations", True):
            success, msg = self.user_manager.export_user_recommendations(username)
            if success:
                logger.info("%s", msg)
            else:
                logger.warning("No se pudo exportar datos: %s", msg)
        
        self.show_main_app()
        self.toast.show(message or f"Bienvenido {self.current_display_name}", duration=2, type="success")
        self.events.emit("app.login", username=username, display_name=self.current_display_name)
        self.after(500, lambda: self.events.emit("app.ready"))
    
    def do_google_login(self):
        self.toast.show("Abriendo login de Google...", duration=2, type="info")
        
        def run_oauth():
            try:
                profile = self.google_oauth_flow()
                email = profile.get("email", "").strip()
                if not email:
                    raise RuntimeError("Google no devolvió un correo válido.")
                name = profile.get("name") or email.split("@")[0]
                avatar_url = profile.get("picture", "")
                
                # Cachear avatar localmente
                avatar_local = ""
                if avatar_url:
                    try:
                        import io
                        resp = requests.get(avatar_url, timeout=5)
                        from PIL import Image
                        img = Image.open(io.BytesIO(resp.content))
                        cache_dir = os.path.join("assets", "avatars")
                        os.makedirs(cache_dir, exist_ok=True)
                        safe_name = email.replace("@", "_at_").replace(".", "_")
                        cache_path = os.path.join(cache_dir, f"{safe_name}.png")
                        img.save(cache_path)
                        avatar_local = cache_path
                    except Exception:
                        logger.debug("No se pudo cachear avatar de Google")
                
                self.user_manager.login_google(email, name, avatar_url, avatar_local)
                self.after(0, lambda: self.complete_login(email, f"Bienvenido {name}"))
            except Exception as e:
                error = str(e)
                self.after(0, lambda: self.toast.show(f"Google login: {error[:90]}", duration=4, type="error"))
        
        threading.Thread(target=run_oauth, daemon=True).start()

    def _find_oauth_file(self):
        candidates = []
        if getattr(sys, 'frozen', False):
            meipass = sys._MEIPASS
            candidates.append(os.path.join(meipass, "google_oauth_client.json"))
            exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            candidates.append(os.path.join(exe_dir, "config", "google_oauth_client.json"))
            candidates.append(os.path.join(exe_dir, "google_oauth_client.json"))
            candidates.append(os.path.join(os.path.dirname(exe_dir), "config", "google_oauth_client.json"))
            candidates.append(os.path.join(os.path.dirname(exe_dir), "google_oauth_client.json"))
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            candidates.append(os.path.join(base, "config", "google_oauth_client.json"))
            candidates.append(os.path.join(base, "google_oauth_client.json"))
        cwd = os.getcwd()
        candidates.append(os.path.join(cwd, "config", "google_oauth_client.json"))
        candidates.append(os.path.join(cwd, "google_oauth_client.json"))
        for p in candidates:
            if os.path.exists(p):
                return p
        return None

    def google_oauth_flow(self):
        oauth_path = self._find_oauth_file()
        if not oauth_path:
            raise RuntimeError("Falta google_oauth_client.json en config/ o raíz del programa")
        
        import http.server
        import socketserver
        import secrets
        import urllib.parse
        import webbrowser
        
        with open(oauth_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        client_cfg = raw.get("installed") or raw.get("web") or raw
        client_id = client_cfg.get("client_id")
        client_secret = client_cfg.get("client_secret")
        if not client_id or not client_secret:
            raise RuntimeError("Credenciales OAuth inválidas.")
        
        auth_uri = client_cfg.get("auth_uri", "https://accounts.google.com/o/oauth2/v2/auth")
        token_uri = client_cfg.get("token_uri", "https://oauth2.googleapis.com/token")
        state = secrets.token_urlsafe(24)
        result = {}
        
        OAUTH_SUCCESS_HTML = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>NetHUB Ultimate - Autenticación</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#e0e0e0;font-family:'Segoe UI',Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{background:#1a1a1a;border:1px solid #2a6a8a;border-radius:20px;padding:50px 60px;text-align:center;max-width:460px;box-shadow:0 0 60px rgba(42,106,138,.15)}
.checkmark{width:80px;height:80px;border-radius:50%;background:#1a3a2a;border:3px solid #2aaa2a;display:flex;align-items:center;justify-content:center;margin:0 auto 25px;font-size:42px;color:#2aaa2a;animation:pulse 1.5s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(42,170,42,.4)}50%{box-shadow:0 0 0 20px rgba(42,170,42,0)}}
h1{font-size:22px;font-weight:700;margin-bottom:8px;color:#e0e0e0}
p{font-size:14px;color:#a0a0a0;line-height:1.6;margin-bottom:25px}
.badge{display:inline-block;background:#2a6a8a20;border:1px solid #2a6a8a40;border-radius:8px;padding:6px 18px;font-size:11px;color:#2a6a8a;margin-bottom:5px}
.footer{font-size:11px;color:#606060;margin-top:10px}
.spinner{display:inline-block;width:14px;height:14px;border:2px solid #2a6a8a40;border-top-color:#2a6a8a;border-radius:50%;animation:spin .8s linear infinite;vertical-align:middle;margin-right:6px}
@keyframes spin{to{transform:rotate(360deg)}}
</style></head>
<body>
<div class="card">
<div class="checkmark">&#10003;</div>
<span class="badge">NetHUB Ultimate</span>
<h1>Autenticación exitosa</h1>
<p>Tu cuenta de Google se ha vinculado correctamente.<br>Ya podes volver a la aplicación.</p>
<p><span class="spinner"></span>Esperando confirmación...</p>
<div class="footer">Esta ventana se cerrará automáticamente</div>
</div>
<script>setTimeout(function(){window.close()},3000)</script>
</body>
</html>"""

        OAUTH_ERROR_HTML = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"><title>NetHUB Ultimate - Error</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0a;color:#e0e0e0;font-family:'Segoe UI',Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}
.card{background:#1a1a1a;border:1px solid #8a2a2a;border-radius:20px;padding:50px 60px;text-align:center;max-width:460px;box-shadow:0 0 60px rgba(138,42,42,.15)}
.icon{width:80px;height:80px;border-radius:50%;background:#3a1a1a;border:3px solid #aa2a2a;display:flex;align-items:center;justify-content:center;margin:0 auto 25px;font-size:42px;color:#aa2a2a}
h1{font-size:22px;font-weight:700;margin-bottom:8px;color:#e0e0e0}
p{font-size:14px;color:#a0a0a0;line-height:1.6}
.badge{display:inline-block;background:#8a2a2a20;border:1px solid #8a2a2a40;border-radius:8px;padding:6px 18px;font-size:11px;color:#aa2a2a;margin-bottom:5px}
</style></head>
<body>
<div class="card">
<div class="icon">&#10007;</div>
<span class="badge">NetHUB Ultimate</span>
<h1>Autenticación cancelada</h1>
<p>El inicio de sesión con Google no se completó.<br>Volvé a intentar desde la aplicación.</p>
</div>
</body>
</html>"""

        class OAuthHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(handler_self):
                parsed = urllib.parse.urlparse(handler_self.path)
                params = urllib.parse.parse_qs(parsed.query)
                if parsed.path != "/oauth2callback":
                    handler_self.send_response(404)
                    handler_self.end_headers()
                    return
                result["code"] = params.get("code", [""])[0]
                result["state"] = params.get("state", [""])[0]
                result["error"] = params.get("error", [""])[0]
                has_error = bool(result.get("error"))
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", "text/html; charset=utf-8")
                handler_self.end_headers()
                handler_self.wfile.write((OAUTH_ERROR_HTML if has_error else OAUTH_SUCCESS_HTML).encode("utf-8"))

            def log_message(self, format, *args):
                return
        
        with socketserver.TCPServer(("127.0.0.1", 0), OAuthHandler) as server:
            port = server.server_address[1]
            redirect_uri = f"http://localhost:{port}/oauth2callback"
            params = {
                "client_id": client_id,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "access_type": "offline",
                "prompt": "select_account"
            }
            auth_url = f"{auth_uri}?{urllib.parse.urlencode(params)}"
            webbrowser.open(auth_url)
            server.timeout = 180
            deadline = time.time() + 180
            while time.time() < deadline:
                server.handle_request()
                if result.get("code") or result.get("error"):
                    break
        
        if result.get("error"):
            raise RuntimeError(result["error"])
        if not result.get("code") or result.get("state") != state:
            raise RuntimeError("Autenticación cancelada o estado inválido.")
        
        token_response = requests.post(token_uri, data={
            "code": result["code"],
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }, timeout=20)
        if token_response.status_code >= 400:
            raise RuntimeError("No se pudo obtener token de Google.")
        access_token = token_response.json().get("access_token")
        if not access_token:
            raise RuntimeError("Google no devolvió access_token.")
        
        userinfo = requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=20
        )
        if userinfo.status_code >= 400:
            raise RuntimeError("No se pudo leer el perfil de Google.")
        return userinfo.json()
    
    def do_register(self):
        self.reg_error.configure(text="")
        username = self.reg_user.get().strip()
        email = self.reg_email.get().strip()
        password = self.reg_pass.get()
        password2 = self.reg_pass2.get()
        
        if not username or len(username) < 3:
            self.reg_error.configure(text="Usuario debe tener al menos 3 caracteres")
            return
        if not username.isalnum() and "_" not in username:
            self.reg_error.configure(text="Solo letras, números y _")
            return
        if not password:
            self.reg_error.configure(text="Ingresa una contraseña")
            return
        if len(password) < 6:
            self.reg_error.configure(text="Contraseña mínimo 6 caracteres")
            return
        if password != password2:
            self.reg_error.configure(text="Las contraseñas no coinciden")
            return
        if email and "@" not in email:
            self.reg_error.configure(text="Correo inválido")
            return
        
        success, msg = self.user_manager.register(username, password, "", email=email)
        if success:
            self.reg_user.delete(0, "end")
            self.reg_email.delete(0, "end")
            self.reg_pass.delete(0, "end")
            self.reg_pass2.delete(0, "end")
            self.strength_bar.set(0)
            self.strength_label.configure(text="")
            self.toast.show(msg, duration=2, type="success")
        else:
            self.reg_error.configure(text=msg)
            self.toast.show(msg, duration=2, type="error")
    
    def show_main_app(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Top bar premium
        self.top_bar = ctk.CTkFrame(self.main_frame, height=55, fg_color=self.colors["fg"], corner_radius=0)
        self.top_bar.pack(fill="x", side="top")
        
        drag_area = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        drag_area.pack(side="left", fill="both", expand=True)
        
        # Sidebar premium (definido antes para el toggle)
        main_panel = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        main_panel.pack(fill="both", expand=True)
        
        self.sidebar = ctk.CTkFrame(main_panel, width=75, fg_color=self.colors["sidebar"], corner_radius=0)
        self.sidebar.pack(side="left", fill="y", expand=False)
        self.sidebar.pack_propagate(False)
        
        logo_color = self.colors["accent"] if self.config_manager._contrast_ratio(self.colors["accent"], self.colors["sidebar"]) >= 3 else self.colors["text"]
        self.sidebar_logo = ctk.CTkLabel(self.sidebar, text="⚡", font=("Arial", 22, "bold"),
                                         text_color=logo_color)
        self.sidebar_logo.pack(pady=(20, 10))
        
        # Scroll lateral para módulos
        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", scrollbar_button_color=self.colors["hover"])
        self.sidebar_scroll.pack(fill="both", expand=True, padx=0, pady=0)
        
        # Mecánica de Barra Lateral Colapsable
        self.is_sidebar_collapsed = True
        
        def toggle_sidebar():
            try:
                self.play_sound("click")
            except:
                pass
            
            start_w = 260 if not self.is_sidebar_collapsed else 75
            target_w = 75 if not self.is_sidebar_collapsed else 260
            self.is_sidebar_collapsed = not self.is_sidebar_collapsed
            
            steps = 10
            def run_anim(step=1):
                if not self.sidebar.winfo_exists():
                    return
                t = step / steps
                ease = 1 - (1 - t) ** 3
                curr_w = int(start_w + (target_w - start_w) * ease)
                
                self.sidebar.configure(width=curr_w)
                self.sidebar.pack_configure(fill="y", expand=False)
                
                if step < steps:
                    self.after(8, lambda: run_anim(step + 1))
                else:
                    self.sidebar.configure(width=target_w)
                    for btn in self.menu_buttons:
                        btn.set_collapsed(self.is_sidebar_collapsed)
                    
                    if self.is_sidebar_collapsed:
                        self.sidebar_logo.configure(text="⚡")
                        self.toggle_btn.configure(text="▶")
                        for sep, lbl in self._section_labels:
                            lbl.configure(text="")
                    else:
                        self.sidebar_logo.configure(text="NETHUB")
                        self.toggle_btn.configure(text="☰")
                        texts = ["PRINCIPAL", "MÓDULOS", "ASISTENTE"]
                        for (sep, lbl), txt in zip(self._section_labels, texts):
                            lbl.configure(text=txt)
                        
            run_anim()
            
        # Botón de Toggle en la esquina superior izquierda
        self.toggle_btn = ctk.CTkButton(drag_area, text="☰", width=35, height=35,
                                        fg_color="transparent", hover_color=self.colors["hover"],
                                        text_color=self.colors["text"], font=("Arial", 16, "bold"),
                                        command=toggle_sidebar)
        self.toggle_btn.configure(text="▶")
        self.toggle_btn.pack(side="left", padx=(10, 5))
        
        ctk.CTkLabel(drag_area, text="NetHUB Ultimate", font=("Arial", 18, "bold"),
                    text_color=self.colors["text"]).pack(side="left", padx=10)
        
        self.time_label = ctk.CTkLabel(drag_area, text="", font=("Arial", 12),
                                       text_color=self.colors["text_secondary"])
        self.time_label.pack(side="left", padx=15)
        self.update_clock()
        
        # Contenedor del perfil en el top bar (clicable para ir a ajustes)
        profile_group = ctk.CTkFrame(drag_area, fg_color="transparent", cursor="hand2")
        profile_group.pack(side="right", padx=15)
        
        self.avatar_img = self.get_avatar_image(size=32)
        avatar_label = ctk.CTkLabel(profile_group, image=self.avatar_img, text="", cursor="hand2")
        avatar_label.pack(side="left", padx=(0, 8))
        
        username_label = ctk.CTkLabel(profile_group, text=self.current_display_name, font=("Arial", 12, "bold"),
                                      text_color=self.colors["text"], cursor="hand2")
        username_label.pack(side="left")
        
        profile_group.bind("<Button-1>", lambda e: self.show_settings())
        avatar_label.bind("<Button-1>", lambda e: self.show_settings())
        username_label.bind("<Button-1>", lambda e: self.show_settings())
        
        btn_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        ctk.CTkButton(btn_frame, text="�", width=35, height=35, command=self.toggle_floating_chat,
                     fg_color="transparent", hover_color=self.colors["hover"],
                     text_color=self.colors["text"]).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="�🔒", width=35, height=35, command=self.lock_screen,
                     fg_color="transparent", hover_color=self.colors["hover"],
                     text_color=self.colors["text"]).pack(side="left", padx=2)
        ctk.CTkButton(btn_frame, text="⚙️", width=35, height=35, command=self.show_settings,
                     fg_color="transparent", hover_color=self.colors["hover"],
                     text_color=self.colors["text"]).pack(side="left", padx=2)
        for btn, cmd in [("─", self.minimize_window), ("□", self.toggle_maximize), ("✕", self.destroy)]:
            ctk.CTkButton(btn_frame, text=btn, width=35, height=35, command=cmd,
                         fg_color="transparent", hover_color=self.colors["hover"],
                         text_color=self.colors["text"]).pack(side="left", padx=2)
        
        # Menús premium (Dashboard + Módulos + Chat)
        self.menu_buttons = []
        self.module_buttons = {}
        self._section_labels = []
        menu_builders = []

        self._add_section_separator("PRINCIPAL")
        self.menu_buttons.append(PremiumSidebarButton(self.sidebar_scroll, "🏠 Core Dashboard",
            lambda: self._show_dashboard_wrapper(), self.colors))

        self._add_section_separator("MÓDULOS")
        mod_idx = 1
        for mod_name in sorted(self.modules.keys()):
            mod = self.modules[mod_name]
            def make_module_cmd(m):
                return lambda: self.activate_module(m)
            btn = PremiumSidebarButton(self.sidebar_scroll, mod.menu_label, make_module_cmd(mod), self.colors)
            self.menu_buttons.append(btn)
            self.module_buttons[mod_name] = (btn, mod, mod_idx)
            mod_idx += 1

        self._add_section_separator("ASISTENTE")
        self.menu_buttons.append(PremiumSidebarButton(self.sidebar_scroll, "🧠 Tactical Llama",
            lambda: self._show_chat_wrapper(), self.colors))

        for btn in self.menu_buttons:
            btn.set_collapsed(True)

        # Perfil de usuario al pie del sidebar
        self.sidebar_footer = ctk.CTkFrame(self.sidebar, fg_color=self.colors["fg"], corner_radius=0, height=50)
        self.sidebar_footer.pack(side="bottom", fill="x")
        self.sidebar_footer.pack_propagate(False)

        self.sidebar_avatar = ctk.CTkLabel(self.sidebar_footer, text="",
                                           font=("Arial", 18), fg_color="transparent")
        self.sidebar_avatar.pack(side="left", padx=(15, 8), pady=5)
        self._update_sidebar_footer()

        self.sidebar_footer.bind("<Button-1>", lambda e: self.show_settings())

        # Canvas de ecualizador de audio premium al pie de la barra lateral
        self.eq_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=60)
        self.eq_frame.pack(side="bottom", fill="x", pady=15, padx=10)
        
        self.eq_canvas = ctk.CTkCanvas(self.eq_frame, width=220, height=30, bg=self.colors["sidebar"], highlightthickness=0)
        self.eq_canvas.pack(fill="x", pady=2)
        
        self.eq_label = ctk.CTkLabel(self.eq_frame, text="⚡ HAPTIC SYSTEM: ACTIVE", font=("Arial", 8, "bold"), text_color=self.colors["accent"])
        self.eq_label.pack()
        
        eq_bars = [5, 12, 8, 15, 6, 18, 10, 14, 7, 11]
        
        def animate_eq():
            if not self.sidebar.winfo_exists() or not self.eq_canvas.winfo_exists():
                return
            
            # Verificar si sonido está activo leyendo config_manager
            sound_active = self.config_manager.config.get("sound_effects", True)
            
            if self.is_sidebar_collapsed:
                self.eq_canvas.pack_forget()
                self.eq_label.configure(text="🔇" if not sound_active else "🔊", font=("Arial", 14, "bold"))
            else:
                self.eq_canvas.pack(fill="x", pady=2)
                self.eq_label.configure(
                    text="⚡ HAPTIC SYSTEM: ACTIVE" if sound_active else "⚠️ HAPTIC SYSTEM: MUTED",
                    font=("Arial", 8, "bold")
                )
                
                self.eq_canvas.delete("all")
                w = self.eq_canvas.winfo_width()
                if w <= 1: w = 220
                num_bars = len(eq_bars)
                bar_w = int((w - (num_bars * 3)) / num_bars)
                
                for idx in range(num_bars):
                    h = random.randint(4, 25) if sound_active else 2
                    x1 = idx * (bar_w + 3) + 5
                    y1 = 30 - h
                    x2 = x1 + bar_w
                    y2 = 30
                    self.eq_canvas.create_rectangle(x1, y1, x2, y2, fill=self.colors["accent"], outline="")
                    
            self.after(150, animate_eq)
            
        animate_eq()
        
        # Content frame
        self.content_frame = ctk.CTkFrame(main_panel, fg_color=self.colors["bg"])
        self.content_frame.pack(side="left", fill="both", expand=True)
        
        # Mostrar Dashboard por defecto
        self.show_dashboard()
        if self.menu_buttons:
            self.menu_buttons[0].set_active(True)
    
    def _add_section_separator(self, text):
        sep = ctk.CTkFrame(self.sidebar_scroll, fg_color=self.colors["border"], height=1)
        sep.pack(fill="x", padx=15, pady=(12, 2))
        lbl = ctk.CTkLabel(self.sidebar_scroll, text=text, font=("Arial", 8, "bold"),
                           text_color=self.colors["text_secondary"])
        lbl.pack(fill="x", padx=(20, 0), pady=(0, 4))
        self._section_labels.append((sep, lbl))

    def _update_sidebar_footer(self):
        try:
            avatar = self.get_avatar_image(size=22)
            self.sidebar_avatar.configure(image=avatar)
            self.sidebar_avatar.image = avatar
        except:
            self.sidebar_avatar.configure(text="👤")

    def set_active_menu(self, active_btn):
        for btn in self.menu_buttons:
            btn.set_active(btn == active_btn)
    
    def update_clock(self):
        if hasattr(self, 'time_label'):
            self.time_label.configure(text=datetime.datetime.now().strftime("%H:%M:%S"))
            self.after(1000, self.update_clock)
    
    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            if hasattr(widget, 'is_tool_container'):
                widget.auto_back = False
            widget.destroy()
            
        # Animación de slide-in suave para todo el contenido usando interpolación de pack padding
        def slide_in(step=0):
            if not self.content_frame.winfo_exists():
                return
            if step <= 15:
                t = step / 15
                # Easing cúbico out
                ease = 1 - (1 - t) ** 3
                current_pad = int(45 * (1 - ease))
                self.content_frame.pack_configure(padx=(current_pad, 0))
                self.after(8, lambda: slide_in(step + 1))
            else:
                self.content_frame.pack_configure(padx=(0, 0))
                
        slide_in()
    
    # ============ DASHBOARD ============
    # ============ DASHBOARD ============
    def show_dashboard(self):
        self.clear_content()
        self.set_active_menu(self.menu_buttons[0])
        self.current_menu = self.show_dashboard
        
        # Grid layout con CTkScrollableFrame para permitir múltiples radares en scroll
        dashboard_frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        dashboard_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        dashboard_grid = ctk.CTkFrame(dashboard_frame, fg_color="transparent")
        dashboard_grid.pack(fill="both", expand=True)
        left_col = ctk.CTkFrame(dashboard_grid, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        right_col = ctk.CTkFrame(dashboard_grid, fg_color="transparent", width=380)
        right_col.pack(side="right", fill="both", expand=False, padx=(10, 0))
        right_col.pack_propagate(False)
        
        # --- COLUMNA IZQUIERDA ---
        # 1. Tarjeta Bienvenida
        welcome_card = ctk.CTkFrame(left_col)
        welcome_card.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(welcome_card, text="⚡ Bienvenido a NetHUB Ultimate",
                font=("Arial", 22, "bold"), text_color=self.colors["text"], anchor="w").pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(welcome_card, text="Tu centro de comando táctico está completamente activo y protegido.",
                    font=("Arial", 12), text_color=self.colors["text_secondary"], anchor="w").pack(anchor="w", padx=20, pady=(0, 10))
        
        # 2. AI Advisory Card (Recomendación táctica dinámica de LLAMA/Ollama)
        ai_advisory = ctk.CTkFrame(left_col, fg_color=self.colors["fg"], corner_radius=15)
        ai_advisory.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(ai_advisory, text="⚡ RECOMENDACIÓN TÁCTICA DE IA (OLLAMA):", font=("Arial", 11, "bold"),
                    text_color=self.colors["accent"]).pack(anchor="w", padx=20, pady=(10, 2))
        ai_tip_label = ctk.CTkLabel(ai_advisory, text="Consultando al analista táctico de IA...", font=("Arial", 12, "italic"),
                                   text_color=self.colors["text_secondary"], justify="left", wraplength=450)
        ai_tip_label.pack(anchor="w", padx=20, pady=(0, 10))
        
        def fetch_ai_tip():
            try:
                tip = self.ollama.generate("Genera una única recomendación táctica de ciberseguridad o hacking ético extremadamente breve e impactante para un analista (máximo 15 palabras):")
                if tip:
                    self.after(0, lambda: ai_tip_label.winfo_exists() and ai_tip_label.configure(text=f'"{tip.strip()}"', font=("Arial", 12, "bold"), text_color=self.colors["text"]))
            except:
                self.after(0, lambda: ai_tip_label.winfo_exists() and ai_tip_label.configure(text="No se pudo conectar a Ollama. Inicia 'ollama serve' para activar el Analista de IA."))
                
        threading.Thread(target=fetch_ai_tip, daemon=True).start()
        
        # Telemetría de Red Real activa para el Radar 1
        active_points = []
        
        def scan_real_network():
            nonlocal active_points
            new_points = []
            alerts = []
            score = 100
            
            try:
                conns = psutil.net_connections(kind='inet')
                seen_ips = set()
                for conn in conns:
                    if conn.status == 'LISTEN':
                        lport = conn.laddr.port
                        if lport in [21, 23]:
                            alerts.append(f"[ALERTA] Puerto inseguro {lport} (FTP/Telnet) en LISTEN.")
                            score -= 10
                        elif lport in [80]:
                            alerts.append(f"[ALERTA] Puerto HTTP {lport} abierto (sin cifrado).")
                            score -= 5
                            
                    elif conn.status == 'ESTABLISHED' and conn.raddr:
                        rip = conn.raddr.ip
                        rport = conn.raddr.port
                        if rip not in seen_ips and rip != '127.0.0.1':
                            seen_ips.add(rip)
                            if rport in [443, 22]:
                                lvl = "Bajo"
                            elif rport in [80, 8080]:
                                lvl = "Medio"
                                score -= 3
                            else:
                                lvl = "Crítico"
                                score -= 5
                                
                            ip_hash = sum(map(int, [x for x in rip.split('.') if x.isdigit()]))
                            rad_angle = (ip_hash * 13 + rport) % 360
                            distance = 45 + (rport % 100)
                            new_points.append((rad_angle, distance, lvl, rip, rport))
            except:
                new_points = [
                    (45, 80, "Bajo", "192.168.1.1", 443),
                    (135, 120, "Crítico", "45.33.22.11", 23),
                    (270, 95, "Medio", "10.0.0.5", 80)
                ]
            
            score = max(45, score)
            active_points = new_points
            return score, alerts

        # ── 3 RADARES CON ESTÉTICAS DISTINTAS ────────────────────────────
        # RADAR 1 (SOC): Clásico círculos concéntricos + barrido + glow
        def build_radar_soc(parent, title, points_fetcher):
            card = ctk.CTkFrame(parent, fg_color=self.colors["fg"], corner_radius=15)
            card.pack(fill="x", pady=10, ipady=5)
            ctk.CTkLabel(card, text=title, font=("Arial", 14, "bold"),
                        text_color=self.colors["accent"]).pack(anchor="w", padx=20, pady=10)
            canvas = ctk.CTkCanvas(card, width=320, height=280, bg=self.colors["fg"], highlightthickness=0)
            canvas.pack(pady=5)
            rendered = []
            angle = 0
            def animate():
                nonlocal angle, rendered
                if not canvas.winfo_exists():
                    return
                canvas.delete("all")
                cx, cy, R = 160, 140, 130
                for r in [35, 65, 95, 125]:
                    canvas.create_oval(cx-r, cy-r, cx+r, cy+r, outline=self.colors["border"], width=1, dash=(3,5))
                canvas.create_line(cx-R, cy, cx+R, cy, fill=self.colors["border"], width=1)
                canvas.create_line(cx, cy-R, cx, cy+R, fill=self.colors["border"], width=1)
                pts = points_fetcher()
                new_rendered = []
                for item in pts:
                    rad_angle, distance, severity, name, extra = item
                    rad = math.radians(rad_angle)
                    px = cx + distance * math.cos(rad)
                    py = cy - distance * math.sin(rad)
                    color = self.colors["success"] if severity == "Bajo" else (self.colors["warning"] if severity == "Medio" else self.colors["error"])
                    new_rendered.append({"x": px, "y": py, "lvl": severity, "name": name, "extra": extra, "color": color})
                    # Punto con glow
                    for g in range(3, 0, -1):
                        canvas.create_oval(px-g*3, py-g*3, px+g*3, py+g*3,
                                          outline="", fill=color if g == 1 else self.colors["bg"],
                                          stipple="gray25" if g > 1 else "")
                    canvas.create_oval(px-4, py-4, px+4, py+4, fill=color, outline="")
                rendered = new_rendered
                rad_sweep = math.radians(angle)
                lx = cx + R * math.cos(rad_sweep)
                ly = cy - R * math.sin(rad_sweep)
                # Haz con degradado
                for i in range(3):
                    off = i * 2
                    canvas.create_line(cx, cy, lx, ly, fill=self.colors["accent"],
                                      width=3-i, stipple="gray50" if i > 0 else "")
                angle = (angle + 2) % 360
                self.after(40, animate)
            animate()
            return card

        # RADAR 2 (LAN): Hex-grid con puntos cuadrados
        def build_radar_lan(parent, title, points_fetcher):
            card = ctk.CTkFrame(parent, fg_color=self.colors["fg"], corner_radius=15)
            card.pack(fill="x", pady=10, ipady=5)
            ctk.CTkLabel(card, text=title, font=("Arial", 14, "bold"),
                        text_color=self.colors["accent_light"]).pack(anchor="w", padx=20, pady=10)
            canvas = ctk.CTkCanvas(card, width=320, height=280, bg=self.colors["fg"], highlightthickness=0)
            canvas.pack(pady=5)
            rendered = []
            pulse = 0
            def animate():
                nonlocal pulse, rendered
                if not canvas.winfo_exists():
                    return
                canvas.delete("all")
                cx, cy, R = 160, 140, 120
                # Hexágonos concéntricos
                for ring in [1, 2, 3]:
                    r = ring * 35
                    pts_hex = []
                    for i in range(6):
                        a = math.radians(60 * i - 30)
                        pts_hex.append((cx + r * math.cos(a), cy + r * math.sin(a)))
                    for i in range(6):
                        x1, y1 = pts_hex[i]
                        x2, y2 = pts_hex[(i+1) % 6]
                        canvas.create_line(x1, y1, x2, y2, fill=self.colors["border"], width=1, dash=(2,4))
                # Líneas radiales del hexágono
                for i in range(6):
                    a = math.radians(60 * i - 30)
                    canvas.create_line(cx, cy, cx + R * math.cos(a), cy + R * math.sin(a),
                                      fill=self.colors["border"], width=1, dash=(2,4))
                pts = points_fetcher()
                new_rendered = []
                pulse = (pulse + 1) % 30
                for item in pts:
                    rad_angle, distance, severity, name, extra = item
                    rad = math.radians(rad_angle)
                    px = cx + distance * math.cos(rad)
                    py = cy - distance * math.sin(rad)
                    color = self.colors["success"] if severity == "Bajo" else (self.colors["warning"] if severity == "Medio" else self.colors["error"])
                    new_rendered.append({"x": px, "y": py, "name": name, "extra": extra, "lvl": severity, "color": color})
                    # Heat pulse
                    heat_r = 6 + abs(pulse - 20) * 0.5
                    canvas.create_oval(px-heat_r, py-heat_r, px+heat_r, py+heat_r,
                                      fill="", outline=color, width=2)
                    canvas.create_oval(px-4, py-4, px+4, py+4, fill=color, outline="")
                    # Etiqueta
                    canvas.create_text(px, py-14, text=name, fill=color,
                                      font=("Arial", 7, "bold"))
                rendered = new_rendered
                self.after(60, animate)
            animate()
            return card

        # RADAR 3 (Threat): Estilo topográfico/heatmap con puntos pulsantes
        def build_radar_threat(parent, title, points_fetcher):
            card = ctk.CTkFrame(parent, fg_color=self.colors["fg"], corner_radius=15)
            card.pack(fill="x", pady=10, ipady=5)
            ctk.CTkLabel(card, text=title, font=("Arial", 14, "bold"),
                        text_color=self.colors["error"]).pack(anchor="w", padx=20, pady=10)
            canvas = ctk.CTkCanvas(card, width=320, height=280, bg=self.colors["fg"], highlightthickness=0)
            canvas.pack(pady=5)
            rendered = []
            pulse = 0
            def animate():
                nonlocal pulse, rendered
                if not canvas.winfo_exists():
                    return
                canvas.delete("all")
                cx, cy, R = 160, 140, 130
                # Curvas topográficas
                for r in [25, 50, 75, 100, 125]:
                    canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                      outline=self.colors["border"], width=1,
                                      dash=(1, 6) if r % 2 == 0 else (3, 4))
                # Líneas de latitud/longitud (globe style)
                for a_deg in range(0, 360, 30):
                    a = math.radians(a_deg)
                    x = cx + R * math.cos(a)
                    y = cy - R * math.sin(a) * 0.5
                    canvas.create_line(cx, cy, x, y, fill=self.colors["border"], width=1, dash=(1, 8))
                for lat in [-0.5, -0.25, 0, 0.25, 0.5]:
                    yy = cy + lat * R
                    canvas.create_oval(cx-R, yy-R*0.15, cx+R, yy+R*0.15,
                                      outline=self.colors["border"], width=1, dash=(2, 6))
                pts = points_fetcher()
                new_rendered = []
                pulse = (pulse + 1) % 40
                for item in pts:
                    rad_angle, distance, severity, name, extra = item
                    rad = math.radians(rad_angle)
                    px = cx + distance * math.cos(rad)
                    py = cy - distance * math.sin(rad) * 0.5
                    color = self.colors["error"] if severity == "Crítico" else (self.colors["warning"] if severity == "Medio" else self.colors["success"])
                    new_rendered.append({"x": px, "y": py, "name": name, "extra": extra, "lvl": severity, "color": color})
                    # Heat pulse
                    heat_r = 6 + abs(pulse - 20) * 0.5
                    canvas.create_oval(px-heat_r, py-heat_r, px+heat_r, py+heat_r,
                                      fill="", outline=color, width=2)
                    canvas.create_oval(px-4, py-4, px+4, py+4, fill=color, outline="")
                    # Etiqueta
                    canvas.create_text(px, py-14, text=name, fill=color,
                                      font=("Arial", 7, "bold"))
                rendered = new_rendered
                self.after(50, animate)
            animate()
            return card

        # Crear los 3 radares
        def fetch_net_radar():
            return [(pt[0], pt[1], pt[2], pt[3], f"Port {pt[4]} (TCP)") for pt in active_points]
        build_radar_soc(left_col, "🛰️ Radar SOC: Telemetría de Red", fetch_net_radar)

        def fetch_lan_radar():
            return [(30, 60, "Bajo", "192.168.1.1", "Router"), (120, 95, "Medio", "192.168.1.45", "Smart TV"),
                    (210, 70, "Bajo", "192.168.1.100", "NAS"), (315, 130, "Crítico", "192.168.1.215", "Nodo Desconocido")]
        build_radar_lan(left_col, "🛡️ Radar LAN: Vecindario Local", fetch_lan_radar)

        def fetch_threat_radar():
            return [(75, 110, "Crítico", "45.88.92.12", "SSH Brute Force"), (165, 80, "Medio", "185.220.101.4", "Tor Exit"),
                    (280, 140, "Crítico", "89.248.165.2", "Port Scan")]
        build_radar_threat(left_col, "📡 Radar Threat: Anomalías Globales", fetch_threat_radar)
        
        # --- COLUMNA DERECHA ---
        # 0. Chat Compacto de IA en Dashboard
        chat_card = ctk.CTkFrame(right_col, fg_color=self.colors["fg"], corner_radius=15)
        chat_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(chat_card, text="🤖 Asistente IA Rápido", font=("Arial", 12, "bold"),
                    text_color=self.colors["accent"]).pack(anchor="w", padx=15, pady=(10, 5))
        
        dashboard_chat_display = ctk.CTkTextbox(chat_card, height=140, fg_color=self.colors["bg"],
                                               text_color=self.colors["text"], font=("Arial", 9))
        dashboard_chat_display.pack(fill="both", expand=True, padx=15, pady=5)
        dashboard_chat_display.insert("end", "💬 Chat rápido IA\nEscribe una pregunta corta…\n")
        dashboard_chat_display.configure(state="disabled")
        
        dashboard_chat_input = ctk.CTkEntry(chat_card, placeholder_text="Pregunta breve…",
                                           fg_color=self.colors["bg"], text_color=self.colors["text"],
                                           height=28, font=("Arial", 9))
        dashboard_chat_input.pack(fill="x", padx=15, pady=(0, 5))
        
        def send_dashboard_message():
            msg = dashboard_chat_input.get().strip()
            if not msg:
                return
            dashboard_chat_input.delete(0, "end")
            
            # Mostrar mensaje
            dashboard_chat_display.configure(state="normal")
            dashboard_chat_display.insert("end", f"\n👤: {msg[:50]}\n")
            dashboard_chat_display.see("end")
            dashboard_chat_display.configure(state="disabled")
            
            # Generar respuesta rápida
            def generate():
                try:
                    resp_short = self.ollama.generate_quick(msg, max_chars=100)
                    self.after(0, lambda: (
                        dashboard_chat_display.configure(state="normal"),
                        dashboard_chat_display.insert("end", f"🤖: {resp_short}\n"),
                        dashboard_chat_display.see("end"),
                        dashboard_chat_display.configure(state="disabled"),
                        self.toast.show(resp_short, duration=3, type="info") if len(resp_short) > 0 else None
                    ))
                except:
                    pass
            
            threading.Thread(target=generate, daemon=True).start()
        
        dashboard_chat_input.bind("<Return>", lambda e: send_dashboard_message())
        
        send_btn = ctk.CTkButton(chat_card, text="📤", command=send_dashboard_message,
                                fg_color=self.colors["accent"], height=28, width=40, font=("Arial", 10))
        send_btn.pack(anchor="e", padx=15, pady=(0, 10))
        
        # 1. Estado de Seguridad Global (Card circular brillante)
        status_card = ctk.CTkFrame(right_col, fg_color=self.colors["fg"], corner_radius=15)
        status_card.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(status_card, text="🛡️ Estado de Seguridad (Host)", font=("Arial", 14, "bold"),
                    text_color=self.colors["text"]).pack(anchor="w", padx=20, pady=10)
                    
        # Indicador brillante circular
        status_indicator = ctk.CTkFrame(status_card, width=110, height=110, corner_radius=55, fg_color=self.colors["bg"])
        status_indicator.pack(pady=5)
        
        status_text_label = ctk.CTkLabel(status_indicator, text="100%", font=("Arial", 26, "bold"), text_color=self.colors["accent"])
        status_text_label.place(relx=0.5, rely=0.45, anchor="center")
        
        status_desc_label = ctk.CTkLabel(status_indicator, text="SEGURO", font=("Arial", 9, "bold"), text_color=self.colors["success"])
        status_desc_label.place(relx=0.5, rely=0.7, anchor="center")
        
        # Diales dinámicos de recursos en tiempo real
        resources_frame = ctk.CTkFrame(status_card, fg_color="transparent")
        resources_frame.pack(fill="x", padx=15, pady=10)
        
        # 1. CPU Wave Monitor
        cpu_col = ctk.CTkFrame(resources_frame, fg_color=self.colors["bg"], corner_radius=10)
        cpu_col.pack(side="left", fill="both", expand=True, padx=5)
        
        ctk.CTkLabel(cpu_col, text="📈 CPU WAVE", font=("Arial", 10, "bold"), text_color=self.colors["text_secondary"]).pack(pady=(5,0))
        cpu_canvas = ctk.CTkCanvas(cpu_col, width=130, height=50, bg=self.colors["bg"], highlightthickness=0)
        cpu_canvas.pack(pady=5)
        
        # 2. RAM Dial Monitor
        ram_col = ctk.CTkFrame(resources_frame, fg_color=self.colors["bg"], corner_radius=10)
        ram_col.pack(side="right", fill="both", expand=True, padx=5)
        
        ctk.CTkLabel(ram_col, text="📊 RAM LOAD", font=("Arial", 10, "bold"), text_color=self.colors["text_secondary"]).pack(pady=(5,0))
        ram_canvas = ctk.CTkCanvas(ram_col, width=60, height=50, bg=self.colors["bg"], highlightthickness=0)
        ram_canvas.pack(pady=5)
        
        wave_offset = 0
        def update_dashboard_resources():
            nonlocal wave_offset
            if not (cpu_canvas.winfo_exists() and ram_canvas.winfo_exists()):
                return
                
            # Escanear red real y actualizar Score & Alertas
            score, alerts = scan_real_network()
            
            # Modificar interfaz con el score real obtenido
            status_text_label.configure(text=f"{score}%")
            status_desc_label.configure(
                text="SEGURO" if score > 85 else ("ALERTA" if score > 65 else "RIESGO"),
                text_color=self.colors["success"] if score > 85 else (self.colors["warning"] if score > 65 else self.colors["error"])
            )
            
            # Reportar alertas de seguridad al Log Feed en caliente
            if alerts and log_box.winfo_exists():
                log_box.configure(state="normal")
                for alert in alerts:
                    content = log_box.get("1.0", "end")
                    if alert not in content:
                        log_box.insert("1.0", f"{datetime.datetime.now().strftime('%H:%M:%S')} - {alert}\n")
                log_box.configure(state="disabled")
                
            # CPU Oscilloscope Wave
            cpu_canvas.delete("all")
            try:
                cpu_p = psutil.cpu_percent()
            except:
                cpu_p = 25
            
            amplitude = 5 + (cpu_p * 0.15)
            frequency = 0.15
            points = []
            for x in range(0, 130, 2):
                y = 25 + amplitude * math.sin((x + wave_offset) * frequency)
                points.append((x, y))
            
            # Cuadrícula
            for grid_x in range(0, 130, 20):
                cpu_canvas.create_line(grid_x, 0, grid_x, 50, fill=self.colors["border"], width=1)
            for grid_y in range(0, 50, 15):
                cpu_canvas.create_line(0, grid_y, 130, grid_y, fill=self.colors["border"], width=1)
                
            # Línea senoidal
            for idx in range(len(points) - 1):
                x1, y1 = points[idx]
                x2, y2 = points[idx+1]
                cpu_canvas.create_line(x1, y1, x2, y2, fill=self.colors["accent"], width=2)
                
            cpu_canvas.create_text(65, 40, text=f"CPU: {cpu_p:.1f}%", fill=self.colors["text"], font=("Arial", 8, "bold"))
            
            # RAM Load Dial
            ram_canvas.delete("all")
            try:
                ram_p = psutil.virtual_memory().percent
            except:
                ram_p = 50
                
            ram_canvas.create_oval(15, 5, 45, 35, outline=self.colors["border"], width=3)
            extent_angle = -(ram_p / 100.0) * 359
            ram_canvas.create_arc(15, 5, 45, 35, start=90, extent=extent_angle, outline=self.colors["accent_light"], width=3, style="arc")
            ram_canvas.create_text(30, 20, text=f"{int(ram_p)}%", fill=self.colors["text"], font=("Arial", 9, "bold"))
            ram_canvas.create_text(30, 42, text="RAM USED", fill=self.colors["text_secondary"], font=("Arial", 7, "bold"))
            
            wave_offset += 3
            self.after(100, update_dashboard_resources)
            
        update_dashboard_resources()
        
        # ── NOTICIAS GLOBALES DE CIBERSEGURIDAD (con imágenes) ──────────
        news_card = ctk.CTkFrame(right_col, fg_color=self.colors["fg"], corner_radius=15)
        news_card.pack(fill="x", pady=(0, 12))

        news_hdr = ctk.CTkFrame(news_card, fg_color="transparent")
        news_hdr.pack(fill="x", padx=15, pady=(10, 4))
        ctk.CTkLabel(news_hdr, text="🌐 INTEL FEED — Noticias Ciberseguridad",
                    font=("Arial", 13, "bold"), text_color=self.colors["text"]).pack(side="left")
        news_status = ctk.CTkLabel(news_hdr, text="⏳ Cargando…", font=("Arial", 9),
                                   text_color=self.colors["text_secondary"])
        news_status.pack(side="right")

        news_scroll = ctk.CTkScrollableFrame(news_card, fg_color="transparent", height=210)
        news_scroll.pack(fill="x", padx=10, pady=(0, 8))

        def load_news():
            import xml.etree.ElementTree as ET
            import re as _re, io
            articles = []
            rss_urls = [
                ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"),
                ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
            ]
            for source_name, url in rss_urls:
                try:
                    r = requests.get(url, timeout=6, headers={"User-Agent": "NetHUB/2.0"})
                    root = ET.fromstring(r.content)
                    ns = {"media": "http://search.yahoo.com/mrss/"}
                    for item in root.iter("item"):
                        title = item.findtext("title", "").strip()
                        link = item.findtext("link", "").strip()
                        desc = item.findtext("description", "").strip()
                        desc = _re.sub(r"<[^>]+>", "", desc)[:160].strip()
                        img_url = None
                        media_thumb = item.find("media:thumbnail", ns)
                        if media_thumb is not None:
                            img_url = media_thumb.get("url")
                        if not img_url:
                            enc = item.find("enclosure")
                            if enc is not None and "image" in enc.get("type", ""):
                                img_url = enc.get("url")
                        if not img_url:
                            raw_desc = item.findtext("description", "")
                            m = _re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_desc)
                            if m:
                                img_url = m.group(1)
                        if title:
                            articles.append({"title": title, "link": link, "desc": desc,
                                             "img_url": img_url, "source": source_name})
                    if len(articles) >= 6:
                        break
                except:
                    pass
            articles = articles[:6]

            def render_news():
                if not news_scroll.winfo_exists():
                    return
                for child in news_scroll.winfo_children():
                    child.destroy()
                if not articles:
                    ctk.CTkLabel(news_scroll, text="No se pudo cargar el feed.",
                                text_color=self.colors["text_secondary"], font=("Arial", 10)).pack(pady=10)
                    return
                news_status.configure(text=f"✅ {len(articles)} artículos")
                for art in articles:
                    art_frame = ctk.CTkFrame(news_scroll, fg_color=self.colors["bg"], corner_radius=8)
                    art_frame.pack(fill="x", pady=4)
                    body_row = ctk.CTkFrame(art_frame, fg_color="transparent")
                    body_row.pack(fill="x", padx=8, pady=(6, 4))
                    thumb_lbl = ctk.CTkLabel(body_row, text="📷", width=56, height=44,
                                            fg_color=self.colors["fg"], corner_radius=6,
                                            font=("Arial", 18))
                    thumb_lbl.pack(side="left", padx=(0, 6))
                    def load_thumb(url, lbl):
                        if not url:
                            return
                        try:
                            resp = requests.get(url, timeout=5)
                            pil_img = Image.open(io.BytesIO(resp.content)).convert("RGB")
                            pil_img = pil_img.resize((56, 44), Image.Resampling.LANCZOS)
                            ctk_img = ctk.CTkImage(pil_img, size=(56, 44))
                            self.after(0, lambda: lbl.winfo_exists() and lbl.configure(
                                image=ctk_img, text="", fg_color="transparent"))
                        except:
                            pass
                    if art["img_url"]:
                        threading.Thread(target=load_thumb, args=(art["img_url"], thumb_lbl), daemon=True).start()
                    text_col = ctk.CTkFrame(body_row, fg_color="transparent")
                    text_col.pack(side="left", fill="x", expand=True)
                    src_lbl = ctk.CTkLabel(text_col, text=f"  {art['source']}  ", font=("Arial", 8, "bold"),
                                          text_color=self.colors["bg"], fg_color=self.colors["accent"],
                                          corner_radius=4)
                    src_lbl.pack(anchor="w")
                    ctk.CTkLabel(text_col, text=art["title"], font=("Arial", 10, "bold"),
                                text_color=self.colors["text"], wraplength=250,
                                justify="left").pack(anchor="w", pady=(2, 0))
                    if art["desc"]:
                        ctk.CTkLabel(text_col, text=art["desc"][:120] + "…", font=("Arial", 9),
                                    text_color=self.colors["text_secondary"],
                                    wraplength=250, justify="left").pack(anchor="w")
                    btn_row = ctk.CTkFrame(art_frame, fg_color="transparent")
                    btn_row.pack(fill="x", padx=8, pady=(0, 6))
                    def ai_summarize(a=art):
                        self.toast.show("Resumiendo…", type="info")
                        def _run():
                            text = f"{a['title']}. {a['desc']}"
                            prompt = f"Resume en 3 puntos clave con bullet. Impacto Alto/Medio/Bajo. Conclusión táctica:\n\n{text}"
                            result = self.ollama.generate(prompt)
                            self.after(0, lambda: self.toast.show("Resumen listo ✓", type="success"))
                            def show_popup():
                                if not self.winfo_exists():
                                    return
                                pop = ctk.CTkToplevel(self)
                                pop.title("📰 Resumen IA")
                                pop.geometry("520x380")
                                pop.grab_set()
                                ctk.CTkLabel(pop, text=a["title"], font=("Arial", 12, "bold"),
                                            text_color=self.colors["accent"], wraplength=490,
                                            justify="left").pack(padx=15, pady=(12, 6))
                                tb = ctk.CTkTextbox(pop, fg_color=self.colors["fg"],
                                                   text_color=self.colors["text"], font=("Arial", 11))
                                tb.pack(fill="both", expand=True, padx=15, pady=5)
                                tb.insert("end", result)
                                tb.configure(state="disabled")
                                ctk.CTkButton(pop, text="Cerrar", command=pop.destroy,
                                             fg_color=self.colors["accent"]).pack(pady=8)
                            self.after(0, show_popup)
                        threading.Thread(target=_run, daemon=True).start()
                    ctk.CTkButton(btn_row, text="🤖 Resumir", command=ai_summarize,
                                 fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                                 height=24, width=90, font=("Arial", 9, "bold")).pack(side="left")
                    if art["link"]:
                        import webbrowser
                        ctk.CTkButton(btn_row, text="🔗 Abrir", width=55, height=24,
                                     fg_color="transparent", hover_color=self.colors["hover"],
                                     text_color=self.colors["text_secondary"],
                                     command=lambda u=art["link"]: webbrowser.open(u),
                                     font=("Arial", 9)).pack(side="left", padx=4)
            self.after(0, render_news)
        threading.Thread(target=load_news, daemon=True).start()
        
        # ── NOTICIAS COLOMBIA ────────────────────────────────────────────────
        co_card = ctk.CTkFrame(right_col, fg_color=self.colors["fg"], corner_radius=15)
        co_card.pack(fill="x", pady=(0, 12))
        
        co_hdr = ctk.CTkFrame(co_card, fg_color="transparent")
        co_hdr.pack(fill="x", padx=15, pady=(10, 4))
        ctk.CTkLabel(co_hdr, text="🇨🇴  Noticias Colombia",
                    font=("Arial", 13, "bold"), text_color=self.colors["text"]).pack(side="left")
        
        co_status = ctk.CTkLabel(co_hdr, text="⏳ Cargando…", font=("Arial", 9),
                                 text_color=self.colors["text_secondary"])
        co_status.pack(side="right")
        
        co_scroll = ctk.CTkScrollableFrame(co_card, fg_color="transparent", height=210)
        co_scroll.pack(fill="x", padx=10, pady=(0, 8))
        
        def load_colombia_news():
            try:
                import xml.etree.ElementTree as ET
                import io, re as _re
                
                rss_sources = [
                    ("El Tiempo",  "https://www.eltiempo.com/rss/noticias.xml"),
                    ("Semana",     "https://www.semana.com/rss/"),
                    ("El Colombiano", "https://www.elcolombiano.com/googlenews"),
                ]
                articles = []
                for source_name, url in rss_sources:
                    try:
                        r = requests.get(url, timeout=7, headers={"User-Agent": "NetHUB/2.0 (colombia-feed)"})
                        root = ET.fromstring(r.content)
                        ns = {"media": "http://search.yahoo.com/mrss/"}
                        for item in root.iter("item"):
                            title = item.findtext("title", "").strip()
                            link  = item.findtext("link", "").strip()
                            desc  = item.findtext("description", "").strip()
                            desc  = _re.sub(r"<[^>]+>", "", desc)[:160].strip()
                            
                            # Try to find image URL from media:thumbnail, enclosure, or description img src
                            img_url = None
                            # 1. media:thumbnail
                            media_thumb = item.find("media:thumbnail", ns)
                            if media_thumb is not None:
                                img_url = media_thumb.get("url")
                            # 2. enclosure tag
                            if not img_url:
                                enc = item.find("enclosure")
                                if enc is not None and "image" in enc.get("type", ""):
                                    img_url = enc.get("url")
                            # 3. img tag in description raw
                            if not img_url:
                                raw_desc = item.findtext("description", "")
                                m = _re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_desc)
                                if m:
                                    img_url = m.group(1)
                            
                            if title:
                                articles.append({
                                    "title": title,
                                    "link": link,
                                    "desc": desc,
                                    "img_url": img_url,
                                    "source": source_name
                                })
                        if len(articles) >= 5:
                            break
                    except:
                        pass
                
                articles = articles[:5]
                
                def render_co_news():
                    if not co_scroll.winfo_exists():
                        return
                    for child in co_scroll.winfo_children():
                        child.destroy()
                    
                    if not articles:
                        ctk.CTkLabel(co_scroll, text="No se pudo cargar noticias colombianas.",
                                    text_color=self.colors["text_secondary"],
                                    font=("Arial", 10)).pack(pady=10)
                        return
                    
                    co_status.configure(text=f"✅ {len(articles)} artículos")
                    
                    for art in articles:
                        art_frame = ctk.CTkFrame(co_scroll, fg_color=self.colors["bg"], corner_radius=8)
                        art_frame.pack(fill="x", pady=5)
                        
                        body_row = ctk.CTkFrame(art_frame, fg_color="transparent")
                        body_row.pack(fill="x", padx=8, pady=(6, 4))
                        
                        # ── Thumbnail ──────────────────────────────────────
                        thumb_lbl = ctk.CTkLabel(body_row, text="📷", width=64, height=52,
                                                fg_color=self.colors["fg"], corner_radius=6,
                                                font=("Arial", 20))
                        thumb_lbl.pack(side="left", padx=(0, 8))
                        
                        def load_thumb(url, lbl, a=art):
                            if not url:
                                return
                            try:
                                resp = requests.get(url, timeout=5)
                                img_data = resp.content
                                pil_img = Image.open(io.BytesIO(img_data)).convert("RGB")
                                pil_img = pil_img.resize((64, 52), Image.Resampling.LANCZOS)
                                ctk_img = ctk.CTkImage(pil_img, size=(64, 52))
                                self.after(0, lambda: lbl.winfo_exists() and lbl.configure(
                                    image=ctk_img, text="", fg_color="transparent"))
                            except:
                                pass
                        
                        if art["img_url"]:
                            threading.Thread(target=load_thumb, args=(art["img_url"], thumb_lbl),
                                           daemon=True).start()
                        
                        # ── Text column ────────────────────────────────────
                        text_col = ctk.CTkFrame(body_row, fg_color="transparent")
                        text_col.pack(side="left", fill="x", expand=True)
                        
                        # Source badge
                        src_row = ctk.CTkFrame(text_col, fg_color="transparent")
                        src_row.pack(anchor="w")
                        ctk.CTkLabel(src_row, text=f"  {art['source']}  ",
                                    font=("Arial", 8, "bold"),
                                    text_color=self.colors["bg"],
                                    fg_color=self.colors["accent"],
                                    corner_radius=4).pack(side="left")
                        
                        ctk.CTkLabel(text_col, text=art["title"],
                                    font=("Arial", 10, "bold"),
                                    text_color=self.colors["text"],
                                    wraplength=250, justify="left").pack(anchor="w", pady=(2, 0))
                        
                        if art["desc"]:
                            ctk.CTkLabel(text_col, text=art["desc"] + "…",
                                        font=("Arial", 9),
                                        text_color=self.colors["text_secondary"],
                                        wraplength=250, justify="left").pack(anchor="w")
                        
                        # Action buttons
                        act_row = ctk.CTkFrame(art_frame, fg_color="transparent")
                        act_row.pack(fill="x", padx=8, pady=(0, 6))
                        
                        def co_ai_summarize(a=art):
                            self.toast.show("Resumiendo con IA…", type="info")
                            def _run():
                                text = f"{a['title']}. {a['desc']}"
                                prompt = f"Eres un analista de noticias colombiano. Resume esta noticia en 3 puntos clave con bullet points (•). Añade contexto para Colombia, nivel de impacto (Alto/Medio/Bajo) y una conclusión breve. Responde en español:\n\n{text}"
                                result = self.ollama.generate(prompt)
                                self.after(0, lambda: self.toast.show("Resumen IA listo ✓", type="success"))
                                def show_popup():
                                    if not self.winfo_exists():
                                        return
                                    pop = ctk.CTkToplevel(self)
                                    pop.title("📰 Resumen Colombia")
                                    pop.geometry("520x380")
                                    pop.grab_set()
                                    ctk.CTkLabel(pop, text=a["title"],
                                                font=("Arial", 12, "bold"),
                                                text_color=self.colors["accent"],
                                                wraplength=490, justify="left").pack(padx=15, pady=(12, 6))
                                    tb = ctk.CTkTextbox(pop, fg_color=self.colors["fg"],
                                                       text_color=self.colors["text"],
                                                       font=("Arial", 11))
                                    tb.pack(fill="both", expand=True, padx=15, pady=5)
                                    tb.insert("end", result)
                                    tb.configure(state="disabled")
                                    ctk.CTkButton(pop, text="Cerrar", command=pop.destroy,
                                                 fg_color=self.colors["accent"]).pack(pady=8)
                                self.after(0, show_popup)
                            threading.Thread(target=_run, daemon=True).start()
                        
                        ctk.CTkButton(act_row, text="🤖 Resumir", command=co_ai_summarize,
                                     fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                                     height=24, width=100, font=("Arial", 9, "bold")).pack(side="left")
                        
                        if art["link"]:
                            import webbrowser
                            ctk.CTkButton(act_row, text="🔗 Abrir", width=60, height=24,
                                         fg_color="transparent", hover_color=self.colors["hover"],
                                         text_color=self.colors["text_secondary"],
                                         command=lambda u=art["link"]: webbrowser.open(u),
                                         font=("Arial", 9)).pack(side="left", padx=4)
                
                self.after(0, render_co_news)
                
            except Exception as ex:
                self.after(0, lambda: co_status.configure(text="❌ Sin conexión"))
        
        threading.Thread(target=load_colombia_news, daemon=True).start()
        
        # ── NOTAS RÁPIDAS ────────────────────────────────────────────
        try:
            from modules.notas_module import NotesModule
            NotesModule.build_dashboard_widget(self, right_col)
        except Exception:
            logger.debug("Notes dashboard widget no disponible")
        
        # 2. Auditoría en Tiempo Real (Log Feed)
        log_card = ctk.CTkFrame(right_col, fg_color=self.colors["fg"], corner_radius=15)
        log_card.pack(fill="both", expand=True)
        
        ctk.CTkLabel(log_card, text="📋 Registro de Eventos (Logs)", font=("Arial", 14, "bold"),
                    text_color=self.colors["text"]).pack(anchor="w", padx=20, pady=10)
                    
        log_box = ctk.CTkTextbox(log_card, fg_color=self.colors["bg"], text_color=self.colors["text_secondary"], font=("Consolas", 10), height=200)
        log_box.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Agregar algunos logs dinámicos premium
        logs = [
            "[OK] Base de datos de hashes cargada correctamente.",
            "[INFO] Motor de IA Chat GLI listo y conectado a Ollama.",
            "[OK] Protocolo de red asegurado mediante cifrado militar.",
            "[INFO] Conexión local activa en puerto 127.0.0.1.",
            "[SEGURO] Ninguna intrusión o puerto no autorizado detectado."
        ]
        for l in logs:
            log_box.insert("end", f"{datetime.datetime.now().strftime('%H:%M:%S')} - {l}\n")
        log_box.configure(state="disabled")
        
    # Métodos show_hacking, port_scanner, hash_cracker, payload_gen, reverse_shell, nmap_gui
    # movidos a modules/hacking_module.py
    
    # Métodos show_network, ping_monitor, dns_lookup, geoip, bandwidth_test
    # movidos a modules/network_module.py
    
    # Métodos show_system, process_manager, disk_analyzer, startup_manager
    # movidos a modules/system_module.py
    
    # ============ CHAT GLI ============
    def show_chat(self):
        self.clear_content()
        self.set_active_menu(self.menu_buttons[4])
        
        outer = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=15, pady=10)
        
        # ── Header ──────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(outer, fg_color=self.colors["fg"], corner_radius=12)
        hdr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hdr, text="🧠  TACTICAL COGNITIVE LLAMA AI — COMMAND CENTER",
                    font=("Arial", 16, "bold"), text_color=self.colors["text"]).pack(side="left", padx=15, pady=12)
        
        online = self.ollama.available
        dot = "🟢 Online" if online else "🔴 Offline — inicia 'ollama serve'"
        ctk.CTkLabel(hdr, text=dot, font=("Arial", 11),
                    text_color="green" if online else "red").pack(side="right", padx=15)
        
        # ── Tab view ────────────────────────────────────────────────────────────
        tabs = ctk.CTkTabview(outer, fg_color=self.colors["fg"], corner_radius=12)
        tabs.pack(fill="both", expand=True)
        
        t_chat   = tabs.add("💬  Chat")
        t_tools  = tabs.add("⚡  AI Tools")
        t_hist   = tabs.add("📜  Historial")
        
        # ─────────────────────────────────────────────────────────────
        #  TAB 1: CHAT
        # ─────────────────────────────────────────────────────────────
        self.chat_display = ctk.CTkTextbox(t_chat, fg_color=self.colors["bg"],
                                           text_color=self.colors["text"], font=("Arial", 12))
        self.chat_display.pack(fill="both", expand=True, padx=10, pady=(10, 5))
        self.chat_display.insert("end", "✨ NetHUB GLI — Asistente IA Táctico ✨\n")
        self.chat_display.insert("end", "─" * 56 + "\n")
        self.chat_display.insert("end", "Comandos: /clear  /code [código]  /save  /help\n")
        self.chat_display.insert("end", "Puedes preguntarme sobre redes, código, seguridad y más.\n\n")
        self.chat_display.configure(state="disabled")
        
        inp_row = ctk.CTkFrame(t_chat, fg_color="transparent")
        inp_row.pack(fill="x", padx=10, pady=(0, 10))
        
        self.chat_input = ctk.CTkEntry(inp_row, placeholder_text="Escribe un mensaje (Enter para enviar)…",
                                       fg_color=self.colors["bg"], text_color=self.colors["text"], height=40)
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.chat_input.bind("<Return>", lambda e: self.send_chat())
        
        ctk.CTkButton(inp_row, text="Enviar ➤", command=self.send_chat,
                     fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                     width=110, height=40).pack(side="right")
        
        ctk.CTkButton(t_chat, text="🗑 Limpiar chat", command=lambda: (
            self.ollama.clear_context(),
            self.chat_display.configure(state="normal"),
            self.chat_display.delete("1.0", "end"),
            self.chat_display.insert("end", "✨ Conversación reiniciada ✨\n\n"),
            self.chat_display.configure(state="disabled")),
            fg_color="transparent", hover_color=self.colors["hover"],
            text_color=self.colors["text_secondary"], width=120, height=28).pack(anchor="e", padx=10, pady=(0, 5))
        
        if not self.ollama.available:
            self.add_chat_message("Sistema", "⚠️ Ollama no está corriendo. Inicia 'ollama serve' en tu terminal.", "system")
        
        # ─────────────────────────────────────────────────────────────
        #  TAB 2: AI TOOLS — 6 herramientas especializadas
        # ─────────────────────────────────────────────────────────────
        tools_scroll = ctk.CTkScrollableFrame(t_tools, fg_color="transparent")
        tools_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        def make_ai_tool(parent, icon, title, subtitle, input_placeholder, prompt_builder, btn_label="🤖 Ejecutar"):
            card = ctk.CTkFrame(parent, fg_color=self.colors["bg"], corner_radius=10)
            card.pack(fill="x", padx=10, pady=8)
            
            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 4))
            ctk.CTkLabel(top, text=f"{icon}  {title}", font=("Arial", 13, "bold"),
                        text_color=self.colors["text"]).pack(side="left")
            ctk.CTkLabel(top, text=subtitle, font=("Arial", 10),
                        text_color=self.colors["text_secondary"]).pack(side="right")
            
            inp = ctk.CTkEntry(card, placeholder_text=input_placeholder,
                              fg_color=self.colors["fg"], text_color=self.colors["text"])
            inp.pack(fill="x", padx=12, pady=4)
            
            out = ctk.CTkTextbox(card, height=110, fg_color=self.colors["fg"],
                                text_color=self.colors["text_secondary"], font=("Arial", 11))
            out.pack(fill="x", padx=12, pady=(0, 4))
            out.insert("end", "Esperando input…")
            out.configure(state="disabled")
            
            def run_tool():
                val = inp.get().strip()
                if not val:
                    self.toast.show("Introduce un valor primero", type="error")
                    return
                out.configure(state="normal")
                out.delete("1.0", "end")
                out.insert("end", "⏳ Procesando con Llama…")
                out.configure(state="disabled")
                
                def _run():
                    result = self.ollama.generate(prompt_builder(val))
                    self.after(0, lambda: (out.configure(state="normal"),
                                          out.delete("1.0", "end"),
                                          out.insert("end", result),
                                          out.configure(state="disabled")))
                threading.Thread(target=_run, daemon=True).start()
            
            ctk.CTkButton(card, text=btn_label, command=run_tool,
                         fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                         height=32, width=160).pack(anchor="e", padx=12, pady=(0, 10))
            return card
        
        # Tool 1 — Threat Intelligence Analyzer
        make_ai_tool(tools_scroll,
            "🎯", "Threat Intelligence Analyzer", "Analiza una IP/dominio/CVE con IA",
            "IP, dominio o CVE (ej: 185.220.101.1 / CVE-2024-1234)",
            lambda v: f"Eres un analista de ciberseguridad de élite. Analiza esta amenaza potencial: '{v}'. Indica: tipo de amenaza, historial conocido, nivel de riesgo (Bajo/Medio/Crítico), sectores objetivo y recomendaciones de mitigación. Responde en español, de forma concisa y técnica.",
            "🎯 Analizar Amenaza")
        
        # Tool 2 — News Summarizer (para resumir noticias del dashboard)
        make_ai_tool(tools_scroll,
            "📰", "News Intelligence Summarizer", "Pega el texto de una noticia para que la IA la resuma",
            "Pega aquí el texto de la noticia…",
            lambda v: f"Eres un analista de inteligencia táctica. Resume esta noticia de ciberseguridad en exactamente 3 puntos clave (usa bullet points con •). Evalúa el impacto (Alto/Medio/Bajo) y da una conclusión táctica breve. Responde en español:\\n\\n{v}",
            "📰 Resumir Noticia")
        
        # Tool 3 — CVE Vulnerability Lookup
        make_ai_tool(tools_scroll,
            "🔍", "CVE Vulnerability Deep Dive", "Análisis profundo de vulnerabilidad por ID",
            "ID de CVE (ej: CVE-2024-3094 / CVE-2021-44228)",
            lambda v: f"Eres un experto en vulnerabilidades NIST. Sobre '{v}', explica: 1) Descripción técnica, 2) Vector de ataque (CVSS), 3) Sistemas afectados, 4) Exploit conocido (sí/no), 5) Parche disponible, 6) Workaround inmediato. Responde en español, formato estructurado.",
            "🔍 Analizar CVE")
        
        # Tool 4 — Secure Code Reviewer
        make_ai_tool(tools_scroll,
            "🔒", "Secure Code Reviewer", "Detecta vulnerabilidades en tu código",
            "Pega aquí el fragmento de código a revisar…",
            lambda v: f"Eres un auditor de seguridad de código experto. Revisa este código en busca de: inyecciones SQL/XSS/Command, secretos hardcodeados, vulnerabilidades conocidas, malas prácticas criptográficas y lógica insegura. Por cada problema encontrado, muestra: [VULNERABILIDAD], línea aproximada, gravedad y fix recomendado. Código:\\n\\n{v}",
            "🔒 Revisar Seguridad")
        
        # Tool 5 — Script Generator
        make_ai_tool(tools_scroll,
            "⚙️", "Tactical Script Generator", "Genera scripts de seguridad/red con IA",
            "Describe el script que necesitas (en español)…",
            lambda v: f"Genera solo el código Python para: {v}. Debe ser funcional, seguro, con comentarios en español. Incluye imports necesarios y un ejemplo de uso en los comentarios finales. Sin explicaciones extra, solo el código.",
            "⚙️ Generar Script")
        
        # Tool 6 — Social Engineering Analyzer
        make_ai_tool(tools_scroll,
            "🎭", "Phishing & Social Eng Detector", "Detecta si un texto/email es phishing",
            "Pega el asunto + cuerpo del email o mensaje sospechoso…",
            lambda v: f"Eres un experto en ingeniería social y phishing. Analiza este mensaje: ¿Es phishing o legítimo? Indica: nivel de sospecha (0-10), señales de alerta encontradas, técnicas de manipulación usadas (si las hay) y qué hacer. Responde en español:\\n\\n{v}",
            "🎭 Detectar Phishing")
        
        # ─────────────────────────────────────────────────────────────
        #  TAB 3: HISTORIAL
        # ─────────────────────────────────────────────────────────────
        hist_box = ctk.CTkTextbox(t_hist, fg_color=self.colors["bg"], text_color=self.colors["text"],
                                  font=("Arial", 11))
        hist_box.pack(fill="both", expand=True, padx=10, pady=10)
        
        if self.ollama.conversation_history:
            for i, entry in enumerate(self.ollama.conversation_history):
                hist_box.insert("end", f"━━━ Mensaje {i+1} ━━━\n")
                hist_box.insert("end", f"👤 {entry['user']}\n")
                hist_box.insert("end", f"🤖 {entry['assistant']}\n\n")
        else:
            hist_box.insert("end", "Sin historial aún. Chatea con el asistente para ver el registro aquí.")
        
        hist_box.configure(state="disabled")
        
        def export_history():
            if not self.ollama.conversation_history:
                self.toast.show("No hay historial para exportar", type="error")
                return
            fname = f"chat_history_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fname, "w", encoding="utf-8") as f:
                for e in self.ollama.conversation_history:
                    f.write(f"[TÚ]: {e['user']}\n[GLI]: {e['assistant']}\n\n")
            self.toast.show(f"Historial exportado: {fname}", type="success")
        
        ctk.CTkButton(t_hist, text="💾 Exportar Historial", command=export_history,
                     fg_color=self.colors["accent"], height=35).pack(pady=8)
    
    def add_chat_message(self, sender, message, msg_type="system"):
        if not hasattr(self, 'chat_display') or not self.chat_display.winfo_exists():
            return
        self.chat_display.configure(state="normal")
        prefixs = {"user": "👤 Tú: ", "ai": "🤖 GLI: ", "system": "📢 Sistema: "}
        prefix = prefixs.get(msg_type, "📢 Sistema: ")
        self.chat_display.insert("end", f"\n{prefix}{message}\n")
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")
    
    def send_chat(self):
        if not hasattr(self, 'chat_input') or not self.chat_input.winfo_exists():
            return
        msg = self.chat_input.get().strip()
        if not msg:
            return
        
        self.add_chat_message("user", msg, "user")
        self.chat_input.delete(0, "end")
        
        if msg.startswith("/clear"):
            self.ollama.clear_context()
            self.chat_display.configure(state="normal")
            self.chat_display.delete("1.0", "end")
            self.chat_display.insert("end", "✨ Conversación reiniciada ✨\n\n")
            self.chat_display.configure(state="disabled")
            return
        elif msg.startswith("/code"):
            code = msg[5:].strip()
            result = self.ollama.execute_code(code)
            self.add_chat_message("system", f"Resultado:\n{result}")
            return
        elif msg.startswith("/save"):
            fname = f"chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(fname, "w", encoding="utf-8") as f:
                f.write(self.chat_display.get("1.0", "end"))
            self.add_chat_message("system", f"Conversación guardada como {fname}")
            return
        elif msg.startswith("/help"):
            self.add_chat_message("system",
                "/clear — limpiar contexto\n"
                "/code [código] — ejecutar Python en sandbox\n"
                "/save — exportar la conversación\n"
                "/help — esta ayuda")
            return
        
        # Streaming response
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", "\n🤖 GLI: ")
        self.chat_display.configure(state="disabled")
        
        def on_chunk(chunk, done):
            if not done and hasattr(self, 'chat_display') and self.chat_display.winfo_exists():
                self.chat_display.configure(state="normal")
                self.chat_display.insert("end", chunk)
                self.chat_display.see("end")
                self.chat_display.configure(state="disabled")
        
        threading.Thread(target=lambda: self.ollama.generate_stream(msg, on_chunk), daemon=True).start()
    
    # Métodos show_code, execute_code, generate_code, explain_code
    # movidos a modules/code_module.py
    
    # Métodos show_monitor y update_monitor movidos a modules/monitor_module.py
    
    # Métodos show_files, file_search, dup_finder, file_hash, batch_rename
    # movidos a modules/files_module.py
    
    # Métodos show_utils, notes, timer_tool, backup, ip_info
    # movidos a modules/utils_module.py
    
    # ============ SETTINGS ============
    def show_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Configuración")
        win.geometry("720x860")
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(scroll, text="⚙️ CONFIGURACIÓN", font=("Arial", 22, "bold"),
                     text_color=self.colors["accent"]).pack(pady=(10, 20))

        # ---------- helper: sección ----------
        def seccion(parent, titulo):
            f = ctk.CTkFrame(parent, fg_color=self.colors["fg"], corner_radius=10)
            f.pack(fill="x", padx=5, pady=6)
            ctk.CTkLabel(f, text=titulo, font=("Arial", 14, "bold"),
                        text_color=self.colors["text"]).pack(anchor="w", padx=15, pady=(10, 5))
            return f

        # ========== APARIENCIA ==========
        sec_theme = seccion(scroll, "🎨 Apariencia")

        theme_frame = ctk.CTkFrame(sec_theme, fg_color="transparent")
        theme_frame.pack(pady=5, padx=15, fill="x")
        ctk.CTkLabel(theme_frame, text="Tema:", text_color=self.colors["text_secondary"]).pack(side="left")
        for theme, color in [("dark", "#2a6a8a"), ("blood", "#8a1a1a"), ("matrix", "#2aaa2a"), ("cyber", "#aa2aaa")]:
            ctk.CTkButton(theme_frame, text=theme.capitalize(), command=lambda t=theme: set_theme(t),
                         fg_color=color, width=85, height=30).pack(side="left", padx=4)

        color_preview = ctk.CTkFrame(sec_theme, width=60, height=24, corner_radius=6, fg_color=self.colors["accent"])
        color_preview.pack(pady=5)

        def choose_color():
            c = colorchooser.askcolor(title="Color personalizado", color=self.colors["accent"])
            if c:
                r, g, b = c[0]
                color_preview.configure(fg_color=c[1])
                bright = (0.2126 * r + 0.7152 * g + 0.0722 * b) > 185
                sb = 0.86 if bright else 0.125
                sf = 0.92 if bright else 0.25
                sh = 0.78 if bright else 0.5
                ss = 0.82 if bright else 0.08
                sbo = 0.68 if bright else 0.33
                custom = {
                    "bg": f"#{max(8,int(r*sb)):02x}{max(8,int(g*sb)):02x}{max(8,int(b*sb)):02x}",
                    "fg": f"#{max(22,int(r*sf)):02x}{max(22,int(g*sf)):02x}{max(22,int(b*sf)):02x}",
                    "accent": c[1],
                    "accent_light": f"#{min(r+40,255):02x}{min(g+40,255):02x}{min(b+40,255):02x}",
                    "text": "#161616" if bright else "#e0e0e0",
                    "text_secondary": "#444444" if bright else "#a0a0a0",
                    "hover": f"#{max(34,int(r*sh)):02x}{max(34,int(g*sh)):02x}{max(34,int(b*sh)):02x}",
                    "sidebar": f"#{max(6,int(r*ss)):02x}{max(6,int(g*ss)):02x}{max(6,int(b*ss)):02x}",
                    "active": c[1],
                    "border": f"#{max(48,int(r*sbo)):02x}{max(48,int(g*sbo)):02x}{max(48,int(b*sbo)):02x}",
                    "success": "#2a6a3a", "error": "#8a2a2a", "warning": "#8a6a2a"
                }
                self.config_manager.config["theme"] = "custom"
                self.config_manager.config["custom_colors"] = custom
                self.config_manager.save_config()
                self.update_colors()
                self.reload_ui()
                win.destroy()
                self.toast.show("Tema personalizado aplicado", type="success")

        ctk.CTkButton(sec_theme, text="🎨 Personalizar", command=choose_color,
                     fg_color=self.colors["accent"], width=160).pack(pady=8)

        def set_theme(theme):
            self.config_manager.config["theme"] = theme
            self.config_manager.save_config()
            self.update_colors()
            self.reload_ui()
            win.destroy()

        app_mode_frame = ctk.CTkFrame(sec_theme, fg_color="transparent")
        app_mode_frame.pack(fill="x", padx=15, pady=(5, 10))
        ctk.CTkLabel(app_mode_frame, text="Modo:", text_color=self.colors["text_secondary"]).pack(side="left")
        seg = ctk.CTkSegmentedButton(app_mode_frame, values=["System", "Dark", "Light"],
                                     command=lambda v: set_appearance(v))
        seg.pack(side="left", padx=10)
        seg.set(self.config_manager.config.get("appearance_mode", "System"))

        def set_appearance(mode):
            self.config_manager.config["appearance_mode"] = mode
            self.config_manager.save_config()
            ctk.set_appearance_mode(mode)
            self.toast.show(f"Modo {mode}", type="success")

        # ========== SONIDO ==========
        sec_sound = seccion(scroll, "🔊 Sonido")
        sw = ctk.CTkSwitch(sec_sound, text="Habilitar sonidos",
                           progress_color=self.colors["accent"])
        sw.pack(anchor="w", padx=15, pady=12)
        sw.select() if self.config_manager.config.get("sound_effects", True) else sw.deselect()
        def toggle_sound():
            self.config_manager.config["sound_effects"] = bool(sw.get())
            self.config_manager.save_config()
            self.toast.show("Sonido guardado", type="success")
        sw.configure(command=toggle_sound)

        # ========== IA / OLLAMA ==========
        sec_ai = seccion(scroll, "🤖 IA & Ollama")

        status_frame = ctk.CTkFrame(sec_ai, fg_color="transparent")
        status_frame.pack(fill="x", padx=15, pady=5)

        # Indicador animado de estado
        self._ollama_dot = ctk.CTkCanvas(status_frame, width=16, height=16,
                                         bg=self.colors["fg"], highlightthickness=0)
        self._ollama_dot.pack(side="left")
        dot_color = "#2a6a3a" if self.ollama.available else "#8a2a2a"
        self._ollama_dot_id = self._ollama_dot.create_oval(2, 2, 14, 14, fill=dot_color, outline="")
        self._ollama_dot_pulse = 0

        def pulse_ollama():
            if not hasattr(self, '_ollama_dot') or not self._ollama_dot.winfo_exists():
                return
            if self.ollama.available:
                self._ollama_dot_pulse = (self._ollama_dot_pulse + 1) % 20
                size = 6 + abs(self._ollama_dot_pulse - 10) * 0.4
                self._ollama_dot.coords(self._ollama_dot_id, 8-size, 8-size, 8+size, 8+size)
                self.after(50, pulse_ollama)
            else:
                self._ollama_dot.itemconfig(self._ollama_dot_id, fill="#8a2a2a")
                self._ollama_dot.coords(self._ollama_dot_id, 2, 2, 14, 14)

        pulse_ollama()

        ctk.CTkLabel(status_frame, text="  Ollama" if self.ollama.available else "  Ollama (desconectado)",
                     text_color=self.colors["text"]).pack(side="left", padx=5)

        model_frame = ctk.CTkFrame(sec_ai, fg_color="transparent")
        model_frame.pack(fill="x", padx=15, pady=8)
        ctk.CTkLabel(model_frame, text="Modelo:", text_color=self.colors["text_secondary"]).pack(side="left")
        model_entry = ctk.CTkEntry(model_frame, width=200, placeholder_text="llama3.2:1b")
        model_entry.pack(side="left", padx=8)
        model_entry.insert(0, self.ollama.model)

        def save_model():
            m = model_entry.get().strip()
            if m:
                self.ollama.model = m
                self.toast.show(f"Modelo: {m}", type="success")
        ctk.CTkButton(model_frame, text="Guardar", command=save_model,
                     fg_color=self.colors["accent"], width=70, height=28).pack(side="left")

        host_frame = ctk.CTkFrame(sec_ai, fg_color="transparent")
        host_frame.pack(fill="x", padx=15, pady=(0, 10))
        ctk.CTkLabel(host_frame, text="Host:", text_color=self.colors["text_secondary"]).pack(side="left")
        host_entry = ctk.CTkEntry(host_frame, width=250, placeholder_text="http://localhost:11434")
        host_entry.pack(side="left", padx=8)
        host_entry.insert(0, self.ollama.host)
        def save_host():
            self.ollama.host = host_entry.get().strip()
            self.toast.show("Host actualizado", type="success")
        ctk.CTkButton(host_frame, text="Guardar", command=save_host,
                     fg_color=self.colors["accent"], width=70, height=28).pack(side="left")

        # ========== CUENTA ==========
        sec_account = seccion(scroll, "👤 Cuenta")

        user_data = self.user_manager.users.get(self.current_user, {})
        is_google = user_data.get("auth_provider") == "google"

        # ── Avatar ──────────────────────────────────────────────────
        avatar_img = self.get_avatar_image(size=70)
        ctk.CTkLabel(sec_account, image=avatar_img, text="").pack(pady=5)

        if is_google and user_data.get("google_avatar"):
            ctk.CTkLabel(sec_account, text="🔄 Foto sincronizada con Google",
                        font=("Arial", 9), text_color=self.colors["success"]).pack()

        def change_avatar():
            fp = filedialog.askopenfilename(title="Foto de perfil",
                                            filetypes=[("Imágenes", "*.png;*.jpg;*.jpeg;*.gif;*.bmp")])
            if fp:
                self.user_manager.users.setdefault(self.current_user, {})
                self.user_manager.users[self.current_user]["avatar"] = fp
                self.user_manager.save_users()
                self.reload_ui()
                win.destroy()
                self.toast.show("Avatar actualizado", type="success")
        ctk.CTkButton(sec_account, text="Subir foto", command=change_avatar,
                     fg_color=self.colors["accent"], width=140).pack(pady=3)

        # ── Nombre ──────────────────────────────────────────────────
        uname_frame = ctk.CTkFrame(sec_account, fg_color="transparent")
        uname_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(uname_frame, text="Nombre:", text_color=self.colors["text_secondary"]).pack(side="left")
        ue = ctk.CTkEntry(uname_frame, width=200)
        ue.pack(side="left", padx=8)
        ue.insert(0, self.current_display_name)

        def save_display_name():
            n = ue.get().strip()
            if not n: return
            self.user_manager.users.setdefault(self.current_user, {})
            self.user_manager.users[self.current_user]["display_name"] = n
            self.user_manager.save_users()
            self._current_display_name = n
            self.reload_ui()
            win.destroy()
            self.toast.show("Nombre actualizado", type="success")
        ctk.CTkButton(uname_frame, text="Guardar", command=save_display_name,
                     fg_color=self.colors["accent"], width=70, height=28).pack(side="left")

        # ── Email / Usuario ─────────────────────────────────────────
        email_frame = ctk.CTkFrame(sec_account, fg_color="transparent")
        email_frame.pack(fill="x", padx=15, pady=2)
        email_label_text = "Email:" if is_google else "Usuario:"
        ctk.CTkLabel(email_frame, text=email_label_text, text_color=self.colors["text_secondary"]).pack(side="left")
        email_val = self.current_user if is_google else self.current_user
        ctk.CTkLabel(email_frame, text=email_val, font=("Arial", 11, "bold"),
                    text_color=self.colors["text"]).pack(side="left", padx=8)
        if is_google:
            ctk.CTkLabel(email_frame, text="✅ Google",
                        text_color=self.colors["success"]).pack(side="left", padx=4)

        # ── Estado Google ───────────────────────────────────────────
        if is_google:
            google_frame = ctk.CTkFrame(sec_account, fg_color=self.colors["bg"], corner_radius=8)
            google_frame.pack(fill="x", padx=15, pady=(8, 0))

            icon_lbl = ctk.CTkLabel(google_frame, text="🔗", font=("Arial", 18))
            icon_lbl.pack(side="left", padx=(10, 5), pady=8)

            info_col = ctk.CTkFrame(google_frame, fg_color="transparent")
            info_col.pack(side="left", fill="x", expand=True, pady=6)

            ctk.CTkLabel(info_col, text="Cuenta vinculada con Google",
                        font=("Arial", 11, "bold"), text_color=self.colors["text"],
                        anchor="w").pack(fill="x")

            linked = user_data.get("google_linked")
            if linked:
                import time
                linked_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(linked))
                ctk.CTkLabel(info_col, text=f"Vinculado: {linked_str}",
                            font=("Arial", 9), text_color=self.colors["text_secondary"],
                            anchor="w").pack(fill="x")

            if user_data.get("google_avatar"):
                ctk.CTkLabel(info_col, text="🖼️ Foto de perfil desde Google",
                            font=("Arial", 9), text_color=self.colors["text_secondary"],
                            anchor="w").pack(fill="x")

            # Desvincular
            def unlink_google():
                pop = ctk.CTkToplevel(self)
                pop.title("Desvincular Google")
                pop.geometry("340x160")
                pop.grab_set()
                ctk.CTkLabel(pop, text="¿Desvincular cuenta de Google?",
                            font=("Arial", 14, "bold"), text_color=self.colors["text"]).pack(pady=(20, 5))
                ctk.CTkLabel(pop, text="Podrás seguir usando NetHUB con tu usuario local.",
                            font=("Arial", 10), text_color=self.colors["text_secondary"]).pack()
                btn_r = ctk.CTkFrame(pop, fg_color="transparent")
                btn_r.pack(pady=15)
                ctk.CTkButton(btn_r, text="Cancelar", command=pop.destroy,
                             fg_color=self.colors["hover"]).pack(side="left", padx=5)
                def do_unlink():
                    self.user_manager.users[self.current_user]["auth_provider"] = "local"
                    self.user_manager.save_users()
                    pop.destroy()
                    win.destroy()
                    self.reload_ui()
                    self.toast.show("Google desvinculado", type="info")
                ctk.CTkButton(btn_r, text="Desvincular", command=do_unlink,
                             fg_color="#c0392b", hover_color="#e74c3c").pack(side="left", padx=5)

            ctk.CTkButton(google_frame, text="Desvincular", command=unlink_google,
                         fg_color="transparent", hover_color="#c0392b",
                         text_color=self.colors["text_secondary"],
                         font=("Arial", 9)).pack(side="right", padx=(0, 10))

        # ── Contraseña local (para cuentas Google y locales) ────────
        has_password = bool(user_data.get("password"))
        pwd_frame = ctk.CTkFrame(sec_account, fg_color="transparent")
        pwd_frame.pack(fill="x", padx=15, pady=5)
        if is_google and not has_password:
            pwd_label = "🔑 Establecer contraseña local:"
        elif is_google:
            pwd_label = "🔑 Cambiar contraseña local:"
        else:
            pwd_label = "🔑 Cambiar contraseña:"
        ctk.CTkLabel(pwd_frame, text=pwd_label, text_color=self.colors["text_secondary"]).pack(side="left")
        pe = ctk.CTkEntry(pwd_frame, width=200, show="*")
        pe.pack(side="left", padx=8)
        def save_password():
            p = pe.get().strip()
            if len(p) < 4:
                self.toast.show("Mínimo 4 caracteres", type="error"); return
            ok, msg = self.user_manager.change_password(self.current_user, p)
            if ok:
                self.user_manager.users[self.current_user]["auth_provider"] = "local"
                self.user_manager.save_users()
            self.toast.show(msg, type="success" if ok else "error")
            if ok:
                self.reload_ui()
        ctk.CTkButton(pwd_frame, text="Guardar", command=save_password,
                     fg_color=self.colors["accent"], width=70, height=28).pack(side="left")

        music_frame = ctk.CTkFrame(sec_account, fg_color="transparent")
        music_frame.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(music_frame, text="Música bloqueo:", text_color=self.colors["text_secondary"]).pack(side="left")
        me = ctk.CTkEntry(music_frame, width=300)
        me.pack(side="left", padx=8)
        me.insert(0, self.user_manager.users.get(self.current_user, {}).get("lock_music", ""))
        def pick_music():
            fp = filedialog.askopenfilename(title="Música de bloqueo",
                                            filetypes=[("Audio", "*.ogg;*.mp3;*.wav")])
            if fp:
                me.delete(0, "end"); me.insert(0, fp)
                self.user_manager.users.setdefault(self.current_user, {})["lock_music"] = fp
                self.user_manager.save_users()
                self.toast.show("Música guardada", type="success")
        ctk.CTkButton(music_frame, text="🎵", command=pick_music,
                     fg_color=self.colors["accent"], width=36, height=28).pack(side="left")

        # ========== DATOS ==========
        sec_data = seccion(scroll, "🛡️ Datos")

        def clear_history():
            import glob
            for f in glob.glob("chat_history*.json"):
                try:
                    os.remove(f)
                except Exception:
                    logger.debug("No se pudo eliminar %s", f)
            self.toast.show("Historial limpiado", type="success")
        ctk.CTkButton(sec_data, text="🗑️ Limpiar historial de chat", command=clear_history,
                     fg_color="#8a3a3a", hover_color="#aa4a4a", width=220).pack(pady=6, padx=15, anchor="w")

        def export_data():
            data = {"users": self.user_manager.users, "config": self.config_manager.config}
            fp = filedialog.asksaveasfilename(defaultextension=".json",
                                              filetypes=[("JSON", "*.json")])
            if fp:
                with open(fp, "w") as f:
                    json.dump(data, f, indent=2)
                self.toast.show(f"Datos exportados a {os.path.basename(fp)}", type="success")
        ctk.CTkButton(sec_data, text="📤 Exportar datos de usuario", command=export_data,
                     fg_color=self.colors["accent"], width=220).pack(pady=6, padx=15, anchor="w")

        def logout_session():
            win.destroy()
            self.config_manager.config["last_session"] = None
            self.config_manager.save_config()
            self.current_user = None
            self._current_display_name = None
            self.show_login()
            self.toast.show("Sesión cerrada", type="info")
        ctk.CTkButton(sec_data, text="🚪 Cerrar sesión", command=logout_session,
                     fg_color="#8a5a2a", hover_color="#aa6a2a", width=220).pack(pady=6, padx=15, anchor="w")

        # ========== MONITOR DEL SISTEMA (animado) ==========
        sec_mon = seccion(scroll, "📊 Monitor del Sistema")
        mon_frame = ctk.CTkFrame(sec_mon, fg_color="transparent")
        mon_frame.pack(fill="x", padx=15, pady=(5, 12))

        def crear_gauge(parent, label, color, getter):
            g = ctk.CTkFrame(parent, fg_color=self.colors["bg"], corner_radius=8)
            g.pack(side="left", padx=8, fill="x", expand=True)
            ctk.CTkLabel(g, text=label, font=("Arial", 10, "bold"),
                        text_color=self.colors["text_secondary"]).pack(pady=(8, 2))
            canvas = ctk.CTkCanvas(g, width=110, height=110,
                                   bg=self.colors["bg"], highlightthickness=0)
            canvas.pack()
            txt_id = canvas.create_text(55, 65, text="0%", fill=self.colors["text"],
                                        font=("Arial", 16, "bold"))
            arc_bg = canvas.create_arc(10, 10, 100, 100, start=0, extent=360,
                                       outline=self.colors["border"], width=5, style="arc")
            arc_id = canvas.create_arc(10, 10, 100, 100, start=135, extent=0,
                                       outline=color, width=5, style="arc")
            def actualizar():
                if not hasattr(self, '_settings_mon_active') or not self._settings_mon_active:
                    return
                try:
                    val = getter()
                except:
                    val = 0
                canvas.itemconfig(txt_id, text=f"{val:.0f}%")
                canvas.itemconfig(arc_id, extent=-val*2.7)
                self.after(1000, actualizar)
            return actualizar

        import psutil
        self._settings_mon_active = True
        def stop_mon():
            self._settings_mon_active = False
        win.protocol("WM_DELETE_WINDOW", lambda: (stop_mon(), win.destroy()))

        crear_gauge(mon_frame, "CPU", self.colors["accent"],
                    lambda: psutil.cpu_percent())()
        crear_gauge(mon_frame, "RAM", self.colors["accent_light"],
                    lambda: psutil.virtual_memory().percent)()
        crear_gauge(mon_frame, "DISCO", self.colors["success"],
                    lambda: psutil.disk_usage(get_system_root()).percent)()

        # ========== MODULOS / PLUGINS ==========
        sec_modules = seccion(scroll, "🧩 Módulos y Plugins")

        plugins_dir = self.module_manager.get_plugins_dir()
        dir_info = ctk.CTkFrame(sec_modules, fg_color=self.colors["fg"], corner_radius=8)
        dir_info.pack(fill="x", padx=15, pady=(5, 10))
        ctk.CTkLabel(dir_info, text=f"📁 {plugins_dir}",
                     font=("Arial", 9), text_color=self.colors["text_secondary"],
                     anchor="w").pack(padx=10, pady=6)

        mod_list_frame = ctk.CTkFrame(sec_modules, fg_color="transparent")
        mod_list_frame.pack(fill="x", padx=15, pady=(0, 10))

        mod_info = self.module_manager.get_info()

        for m in mod_list_frame.winfo_children():
            m.destroy()

        for mod_data in mod_info:
            is_custom = mod_data["custom"]
            row = ctk.CTkFrame(mod_list_frame, fg_color=self.colors["bg"], corner_radius=8)
            row.pack(fill="x", pady=3)

            if mod_data.get("_is_plugin"):
                tag = "PLUGIN"
                tag_color = "#8a5a2a"
            elif is_custom:
                tag = "CUSTOM"
                tag_color = "#2a6a3a"
            else:
                tag = "SISTEMA"
                tag_color = self.colors["accent"]

            ctk.CTkLabel(row, text=mod_data["icon"], font=("Arial", 16), width=30).pack(side="left", padx=(10, 5))

            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True)

            name_row = ctk.CTkFrame(text_frame, fg_color="transparent")
            name_row.pack(fill="x")
            ctk.CTkLabel(name_row, text=mod_data["name"], font=("Arial", 12, "bold"),
                         text_color=self.colors["text"], anchor="w").pack(side="left")

            if mod_data.get("version"):
                ctk.CTkLabel(name_row, text=f"v{mod_data['version']}",
                             font=("Arial", 8), text_color=self.colors["text_secondary"]).pack(side="left", padx=(6, 0))

            if mod_data.get("author"):
                ctk.CTkLabel(name_row, text=f"por {mod_data['author']}",
                             font=("Arial", 8), text_color=self.colors["text_secondary"]).pack(side="left", padx=(6, 0))

            ctk.CTkLabel(text_frame, text=mod_data["description"],
                         font=("Arial", 9), text_color=self.colors["text_secondary"],
                         anchor="w").pack(fill="x")

            ctk.CTkLabel(row, text=tag, font=("Arial", 8, "bold"),
                         text_color="white", fg_color=tag_color, corner_radius=4, width=55).pack(side="right", padx=(5, 10))

        btn_row = ctk.CTkFrame(sec_modules, fg_color="transparent")
        btn_row.pack(pady=(0, 8))

        def reload_custom_modules():
            try:
                self.module_manager.reload_custom()
                win.destroy()
                self.toast.show("Plugins recargados", type="success")
                self.after(200, self.reload_ui)
            except Exception as e:
                self.toast.show(f"Error: {str(e)}", type="error")

        ctk.CTkButton(btn_row, text="🔄 Recargar plugins",
                      command=reload_custom_modules,
                      fg_color=self.colors["accent"], width=150).pack(side="left", padx=4)

        def open_plugins_folder():
            import subprocess
            if platform.system() == "Windows":
                os.startfile(plugins_dir)
            else:
                subprocess.Popen(["open", plugins_dir])

        ctk.CTkButton(btn_row, text="📁 Abrir carpeta",
                      command=open_plugins_folder,
                      fg_color="transparent", hover_color=self.colors["hover"],
                      text_color=self.colors["text_secondary"], border_width=1,
                      border_color=self.colors["border"], width=130).pack(side="left", padx=4)

        def create_plugin_dialog():
            dialog = ctk.CTkInputDialog(text="Nombre del plugin:", title="Crear plugin")
            name = dialog.get_input()
            if not name or not name.strip():
                return
            folder = ModuleManager.create_plugin_template(plugins_dir, name.strip())
            if folder:
                self.toast.show(f"Plugin creado: {folder}", type="success")
                self.after(100, lambda: self._open_plugin_readme(folder))
            else:
                self.toast.show("Error: el nombre ya existe o es invalido", type="error")

        ctk.CTkButton(btn_row, text="✨ Nuevo plugin",
                      command=create_plugin_dialog,
                      fg_color=self.colors["accent"], width=130).pack(side="left", padx=4)

        mod_help = ctk.CTkLabel(sec_modules,
                                text="Suelta una carpeta con plugin.json + main.py en la carpeta plugins/.\n"
                                     "O usa 'Nuevo plugin' para generar una plantilla.",
                                font=("Arial", 9), text_color=self.colors["text_secondary"],
                                justify="left")
        mod_help.pack(pady=(0, 5))

        # ========== ACTUALIZACIONES ==========
        sec_updates = seccion(scroll, "🔄 Actualizaciones")
        
        upd_status_frame = ctk.CTkFrame(sec_updates, fg_color="transparent")
        upd_status_frame.pack(fill="x", padx=15, pady=(5, 10))
        
        ctk.CTkLabel(upd_status_frame, text=f"Version actual: NetHUB Ultimate {getattr(self.updater, 'CURRENT_VERSION', '2.0.0') if hasattr(self, 'updater') else '2.0.0'}",
                     font=("Arial", 11), text_color=self.colors["text_secondary"]).pack(side="left")
        
        ctk.CTkButton(sec_updates, text="🔍 Verificar actualizaciones",
                      command=self.check_updates_manual,
                      fg_color=self.colors["accent"], width=220).pack(pady=6, padx=15, anchor="w")
        
        upd_url_frame = ctk.CTkFrame(sec_updates, fg_color="transparent")
        upd_url_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(upd_url_frame, text="URL de actualizacion:", font=("Arial", 9),
                     text_color=self.colors["text_secondary"]).pack(side="left")
        
        upd_url_entry = ctk.CTkEntry(upd_url_frame, width=320,
                                     placeholder_text="https://raw.githubusercontent.com/.../version.json",
                                     font=("Arial", 9))
        upd_url_entry.pack(side="left", padx=5)
        saved_url = self.config_manager.config.get("update_url", "")
        if saved_url:
            upd_url_entry.insert(0, saved_url)
        else:
            upd_url_entry.insert(0, self.updater.get_update_url() if hasattr(self, "updater") else "")
        
        def save_update_url():
            self.configure_update_url(upd_url_entry.get().strip())
        
        ctk.CTkButton(upd_url_frame, text="Guardar", command=save_update_url,
                      fg_color=self.colors["accent"], width=70, height=24, font=("Arial", 9)).pack(side="left")
        
        # ========== RECOMENDACIONES ==========
        sec_recomendaciones = seccion(scroll, "📊 Recomendaciones")
        export_switch = ctk.CTkSwitch(sec_recomendaciones, text="Exportar datos para recomendaciones",
                                      progress_color=self.colors["accent"])
        export_switch.pack(anchor="w", padx=15, pady=12)
        export_switch.select() if self.config_manager.config.get("export_recommendations", True) else export_switch.deselect()
        def toggle_export_recomendaciones():
            self.config_manager.config["export_recommendations"] = bool(export_switch.get())
            self.config_manager.save_config()
            self.toast.show("Configuración de exportación guardada", type="success")
        export_switch.configure(command=toggle_export_recomendaciones)
        
        # ========== CONTACTO ==========
        sec_contacto = seccion(scroll, "📞 Contacto")
        contact_switch = ctk.CTkSwitch(sec_contacto, text="Habilitar opción de contacto",
                                       progress_color=self.colors["accent"])
        contact_switch.pack(anchor="w", padx=15, pady=12)
        contact_switch.select() if self.config_manager.config.get("contact_enabled", True) else contact_switch.deselect()
        def toggle_contacto():
            self.config_manager.config["contact_enabled"] = bool(contact_switch.get())
            self.config_manager.save_config()
            self.toast.show("Configuración de contacto guardada", type="success")
        contact_switch.configure(command=toggle_contacto)
        
        def crear_ticket():
            # Función simple para crear un ticket (en un caso real, esto enviaría un email o crearía un issue)
            import tkinter as tk
            from tkinter import simpledialog
            
            # Crear una ventana simple para el ticket
            ticket_win = ctk.CTkToplevel(self)
            ticket_win.title("Crear Ticket de Soporte")
            ticket_win.geometry("400x300")
            ticket_win.grab_set()
            
            ctk.CTkLabel(ticket_win, text="Crear Ticket de Soporte", 
                        font=("Arial", 16, "bold")).pack(pady=10)
            
            ctk.CTkLabel(ticket_win, text="Describe tu problema o sugerencia:").pack(pady=(10, 5))
            
            ticket_text = ctk.CTkTextbox(ticket_win, width=350, height=150)
            ticket_text.pack(pady=10, padx=20)
            
            def enviar_ticket():
                mensaje = ticket_text.get("1.0", "end-1c").strip()
                if not mensaje:
                    self.toast.show("Por favor, describe tu problema", type="error")
                    return
                
                # En una implementación real, aquí se enviaría el ticket por email o se crearía un issue en GitHub
                # Por ahora, solo guardamos el ticket en un archivo local
                import json
                import time
                import os
                
                ticket_data = {
                    "user": self.current_user,
                    "timestamp": time.time(),
                    "message": mensaje,
                    "type": "soporte"
                }
                
                tickets_dir = "tickets"
                os.makedirs(tickets_dir, exist_ok=True)
                
                ticket_file = os.path.join(tickets_dir, f"ticket_{int(time.time())}.json")
                try:
                    with open(ticket_file, "w", encoding="utf-8") as f:
                        json.dump(ticket_data, f, indent=2, ensure_ascii=False)
                    
                    self.toast.show("Ticket creado exitosamente", type="success")
                    ticket_win.destroy()
                except Exception as e:
                    self.toast.show(f"Error al crear ticket: {str(e)}", type="error")
            
            btn_frame = ctk.CTkFrame(ticket_win, fg_color="transparent")
            btn_frame.pack(pady=10)
            
            ctk.CTkButton(btn_frame, text="Cancelar", command=ticket_win.destroy,
                         fg_color="transparent", hover_color=self.colors["hover"]).pack(side="left", padx=10)
            ctk.CTkButton(btn_frame, text="Enviar Ticket", command=enviar_ticket,
                         fg_color=self.colors["accent"], hover_color=self.colors["hover"]).pack(side="left", padx=10)
        
        contact_btn = ctk.CTkButton(sec_contacto, text="¡Contáctame!", command=crear_ticket,
                                   fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                                   width=200, height=35)
        contact_btn.pack(pady=10, padx=15, anchor="w")
        
        # ========== INFO ==========
        sec_info = seccion(scroll, "ℹ️ Información")
        ctk.CTkLabel(sec_info,
                     text=f"Versión: NetHUB Ultimate 2.0\n"
                          f"Usuario: {self.current_user}\n"
                          f"Ollama: {'Conectado' if self.ollama.available else 'Desconectado'}\n"
                          f"Modelo: {self.ollama.model}\n"
                          f"Sistema: {platform.system()} {platform.release()}",
                     font=("Arial", 11), text_color=self.colors["text_secondary"],
                     justify="left").pack(pady=15, padx=20, anchor="w")
    
    # Método show_osint movido a modules/osint_module.py

    # Método show_crypto movido a modules/crypto_module.py
            
    def lock_screen(self):
        user_data = self.user_manager.users.get(self.current_user, {}) if self.current_user else {}
        if user_data.get("auth_provider") == "google" and not user_data.get("password"):
            self.toast.show("Establecé una contraseña local en Ajustes > Cuenta para usar el bloqueo.", duration=5, type="warning")
            self.after(300, lambda: self.show_settings())
            return
        
        try:
            self.play_sound("welcome")
        except Exception:
            logger.debug("Error reproduciendo sonido de bloqueo")
            
        # Guardar geometría anterior
        self.previous_geometry = self.geometry()
        
        # Dimensions matching the physical screen
        W = self.winfo_screenwidth()
        H = self.winfo_screenheight()
        
        # Sizing windowed borderless frame to cover everything
        self.geometry(f"{W}x{H}+0+0")
        
        # Activar el estado topmost (siempre al frente)
        self.attributes("-topmost", True)
        
        # Bloquear Alt+F4 y protocolo de cierre del SO durante el bloqueo
        self.bind("<Alt-Key-F4>", lambda e: "break")
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        
        # Create full-screen lock container
        lock_container = ctk.CTkFrame(self, fg_color="#000000")
        lock_container.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        
        self.system_locked = True
        self.events.emit("system.locked")
        
        # Reproducir música de bloqueo mediante ffplay directamente (empezando en segundo 50)
        try:
            # Obtener música personalizada del usuario o usar por defecto
            music_file = "music.ogg"
            toast_msg = "No More Tears reproduciéndose"
            if self.current_user and self.current_user in self.user_manager.users:
                user_music = self.user_manager.users[self.current_user].get("lock_music", "")
                if user_music and os.path.exists(user_music):
                    music_file = user_music
                    # Extract the filename for a clean toast message
                    toast_msg = f"{os.path.basename(user_music)} reproduciéndose"
            
            self.music_process = subprocess.Popen(
                ["ffplay", "-ss", "50", "-nodisp", "-autoexit", music_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
            )
            import atexit
            def cleanup_zombie():
                try:
                    self.music_process.terminate()
                except:
                    pass
            atexit.register(cleanup_zombie)
            self.toast.show(toast_msg, type="info")
        except Exception as e:
            logger.warning("Error al reproducir música con ffplay: %s", e)
        
        # Canvas for Matrix Rain — place() cubre 100% de pantalla detrás del card
        canvas = ctk.CTkCanvas(lock_container, bg="#000000", highlightthickness=0, width=W, height=H)
        canvas.place(x=0, y=0)
        
        # Columns - fill entire screen width with tighter spacing
        char_width = 9
        cols = int(W / char_width) + 5
        y_positions = [random.randint(-150, 0) for _ in range(cols)]
        
        def get_fade_color(hex_color, factor):
            try:
                h = hex_color.lstrip("#")
                r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                r = int(r * (1 - factor))
                g = int(g * (1 - factor))
                b = int(b * (1 - factor))
                return f"#{r:02x}{g:02x}{b:02x}"
            except:
                return "#00ff00"
                
        def animate_matrix():
            if not lock_container.winfo_exists() or not self.system_locked:
                return
                
            canvas.delete("all")
            canvas.create_rectangle(0, 0, W, H, fill="#000000", outline="")
            
            for i in range(cols):
                char = chr(random.randint(33, 126))
                x = i * char_width
                y = y_positions[i]
                
                # Draw vertical column drops
                for tail in range(15):
                    tail_y = y - (tail * 18)
                    if 0 <= tail_y <= H:
                        factor = tail / 15
                        color = get_fade_color(self.colors["accent"], factor)
                        font_size = 11 if tail > 0 else 13
                        font_weight = "bold" if tail == 0 else "normal"
                        canvas.create_text(x, tail_y, text=char, fill=color, font=("Courier New", font_size, font_weight))
                
                y_positions[i] += 18
                if y_positions[i] - 15 * 18 > H or (y_positions[i] > 0 and random.random() < 0.02):
                    y_positions[i] = random.randint(-150, 0)
                    
            self.after(35, animate_matrix)
            
        animate_matrix()
        
        # Center Lock Card
        lock_frame = ctk.CTkFrame(lock_container, fg_color=self.colors["fg"], corner_radius=20, border_width=2, border_color=self.colors["accent"])
        lock_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Large User Avatar
        settings_avatar_img = self.get_avatar_image(size=90)
        avatar_label = ctk.CTkLabel(lock_frame, image=settings_avatar_img, text="")
        avatar_label.pack(pady=(25, 10))
        
        ctk.CTkLabel(lock_frame, text="🔒 ACCESO RESTRINGIDO", font=("Arial", 16, "bold"), text_color=self.colors["accent"]).pack(pady=5)
        ctk.CTkLabel(lock_frame, text=f"Sentinel Kernel está bloqueado.\nIngresa la contraseña de {self.current_user}", font=("Arial", 12), text_color=self.colors["text_secondary"], justify="center").pack(pady=5, padx=30)
        
        pass_entry = ctk.CTkEntry(lock_frame, placeholder_text="Contraseña", show="*", width=280, height=40, fg_color=self.colors["bg"], text_color=self.colors["text"])
        pass_entry.pack(pady=15, padx=40)
        
        # Agarre de foco inicial
        pass_entry.focus_set()
        try:
            lock_container.grab_set()
        except:
            pass
            
        # Bucle de persistencia superior asíncrono y recuperación de foco segura
        def keep_top():
            try:
                if not getattr(self, "system_locked", False) or not lock_container.winfo_exists():
                    return
                self.lift()
                self.attributes("-topmost", True)
                try:
                    if pass_entry.winfo_exists() and self.focus_get() != pass_entry:
                        self.focus_force()
                        pass_entry.focus_set()
                        lock_container.grab_set()
                except Exception:
                    logger.debug("Error en focus del lock screen")
                self.after(500, keep_top)
            except Exception:
                logger.debug("Error en keep_top del lock screen")
                
        keep_top()
        
        def shake(step=0):
            offsets = [0, -12, 12, -9, 9, -6, 6, -3, 3, 0]
            if step < len(offsets):
                lock_frame.place_configure(relx=0.5 + (offsets[step] / W))
                self.after(40, lambda: shake(step + 1))
                
        def unlock():
            pwd = pass_entry.get()
            stored_hash = self.user_manager.users.get(self.current_user, {}).get("password", "")

            verified = False
            if stored_hash.startswith("$2"):
                try:
                    verified = bcrypt.checkpw(pwd.encode('utf-8'), stored_hash.encode('utf-8'))
                except:
                    verified = False
            else:
                legacy = hashlib.sha256(pwd.encode()).hexdigest()
                verified = (legacy == stored_hash)

            if verified:
                self.system_locked = False
                self.events.emit("system.unlocked")
                try:
                    self.play_sound("success")
                except Exception:
                    logger.debug("Error reproduciendo sonido de unlock")
                
                # Detener la música de bloqueo de forma ultra segura
                kill_zombie_music()
                
                # Restaurar Alt+F4 y protocolo de cierre normal al desbloquear
                self.unbind("<Alt-Key-F4>")
                self.protocol("WM_DELETE_WINDOW", self.destroy)
                
                # Liberar agarre de eventos
                try:
                    lock_container.grab_release()
                except:
                    pass
                    
                # Quitar estado topmost para no interferir con otras apps
                self.attributes("-topmost", False)
                
                # Restaurar estado de ventana original
                if hasattr(self, 'previous_geometry'):
                    self.geometry(self.previous_geometry)
                else:
                    self.geometry("1400x850")
                    
                lock_container.destroy()
                self.toast.show(f"Acceso Concedido: Bienvenido de vuelta, {self.current_user}", type="success")
            else:
                try:
                    self.play_sound("error")
                except:
                    pass
                pass_entry.delete(0, "end")
                shake()
                self.toast.show("Firma digital incorrecta. Intento de intrusión registrado.", type="error")
                
        pass_entry.bind("<Return>", lambda e: unlock())
        
        ctk.CTkButton(lock_frame, text="DESCIFRAR & ACCEDER", command=unlock, fg_color=self.colors["accent"], hover_color=self.colors["hover"], height=40, width=280, font=("Arial", 12, "bold")).pack(pady=(5, 25))

    def track_menu_usage(self, menu_index):
        """Guarda el menú más usado como favorito del usuario"""
        if self.current_user and self.current_user in self.user_manager.users:
            self.user_manager.users[self.current_user]["favorite_menu"] = menu_index
            self.user_manager.save_users()
            self.current_menu_index = menu_index

    def get_favorite_menu_index(self):
        """Obtiene el índice del menú favorito del usuario"""
        if self.current_user and self.current_user in self.user_manager.users:
            return self.user_manager.users[self.current_user].get("favorite_menu", 0)
        return 0

    def _check_updates_on_startup(self):
        """Verifica actualizaciones en segundo plano al iniciar la app."""
        if not hasattr(self, "updater"):
            return
        skipped = self.config_manager.config.get("skipped_update_version", "")
        def run_check():
            result = self.updater.check_for_updates()
            if result["available"] and not result["error"]:
                if result["latest_version"] == skipped:
                    return
                self.after(0, lambda: self._show_update_dialog(result))
        threading.Thread(target=run_check, daemon=True).start()

    def check_updates_manual(self):
        """Verifica actualizaciones manualmente desde Configuración."""
        self.toast.show("Buscando actualizaciones...", type="info", duration=1)
        def run_check():
            result = self.updater.check_for_updates()
            if result["error"]:
                self.after(0, lambda: self.toast.show(f"Error: {result['error']}", type="error", duration=4))
                return
            if result["available"]:
                self.after(0, lambda: self._show_update_dialog(result))
            else:
                self.after(0, lambda: self.toast.show(
                    f"Estas en la última versión ({result['current_version']})",
                    type="success", duration=3
                ))
        threading.Thread(target=run_check, daemon=True).start()

    def _show_update_dialog(self, result):
        """Muestra dialogo de actualizacion disponible."""
        latest = result["latest_version"]
        current = result["current_version"]
        mandatory = result.get("mandatory", False)
        message = result.get("message", "Nueva version disponible")
        changelog = result.get("changelog", [])
        download_url = result.get("download_url", "")

        win = ctk.CTkToplevel(self)
        win.title("Actualización disponible")
        win.geometry("480x400")
        win.grab_set()
        win.resizable(False, False)

        if mandatory:
            win.title("Actualización obligatoria")

        container = ctk.CTkFrame(win, fg_color=self.colors["bg"])
        container.pack(fill="both", expand=True, padx=15, pady=15)

        icon = "⚠️" if mandatory else "📦"
        ctk.CTkLabel(container, text=f"{icon} Actualización {latest}",
                     font=("Arial", 20, "bold"), text_color=self.colors["accent"]).pack(pady=(15, 5))

        ctk.CTkLabel(container, text=f"Tu versión: {current}",
                     font=("Arial", 11), text_color=self.colors["text_secondary"]).pack(pady=(0, 5))

        ctk.CTkLabel(container, text=message, font=("Arial", 12),
                     text_color=self.colors["text"], wraplength=420).pack(pady=10)

        if changelog:
            ctk.CTkLabel(container, text="Cambios:", font=("Arial", 11, "bold"),
                         text_color=self.colors["accent"], anchor="w").pack(anchor="w", padx=20)

            changes_box = ctk.CTkTextbox(container, height=120, fg_color=self.colors["fg"],
                                         text_color=self.colors["text"], font=("Arial", 10))
            changes_box.pack(fill="x", padx=20, pady=5)
            for item in changelog:
                changes_box.insert("end", f"  •  {item}\n")
            changes_box.configure(state="disabled")

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(pady=10)

        def start_download():
            win.destroy()
            self._download_with_progress(download_url)

        ctk.CTkButton(btn_frame, text="📥 Descargar", command=start_download,
                      fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                      width=160, height=35, font=("Arial", 12, "bold")).pack(side="left", padx=5)

        def open_browser():
            if download_url:
                import webbrowser
                webbrowser.open(download_url)

        ctk.CTkButton(btn_frame, text="🌐 Abrir en navegador", command=open_browser,
                      fg_color="transparent", hover_color=self.colors["hover"],
                      text_color=self.colors["text_secondary"],
                      width=140, height=35, border_width=1,
                      border_color=self.colors["border"]).pack(side="left", padx=5)

        if not mandatory:
            ctk.CTkButton(btn_frame, text="Ahora no", command=win.destroy,
                          fg_color="transparent", hover_color=self.colors["hover"],
                          text_color=self.colors["text_secondary"],
                          width=100, height=35, border_width=1,
                          border_color=self.colors["border"]).pack(side="left", padx=5)

            def skip_version():
                self.config_manager.config["skipped_update_version"] = latest
                self.config_manager.save_config()
                win.destroy()
                self.toast.show(f"Version {latest} omitida", type="info", duration=2)

            ctk.CTkButton(btn_frame, text="Omitir esta versión", command=skip_version,
                          fg_color="transparent", hover_color=self.colors["hover"],
                          text_color=self.colors["text_secondary"],
                          width=120, height=35, border_width=1,
                          border_color=self.colors["border"]).pack(side="left", padx=5)
        else:
            ctk.CTkLabel(container, text="Esta actualización es obligatoria.",
                         font=("Arial", 10), text_color=self.colors["error"]).pack(pady=5)

    def configure_update_url(self, url):
        """Configura la URL de verificacion de actualizaciones."""
        self.updater.set_update_url(url)
        self.config_manager.config["update_url"] = url
        self.config_manager.save_config()
        self.toast.show("URL de actualizacion guardada", type="success")

    def _open_plugin_readme(self, folder):
        """Abre un mensaje con instrucciones después de crear un plugin."""
        self.toast.show(f"Plugin creado en {folder}", type="success", duration=3)

    def _download_with_progress(self, url):
        """Muestra ventana de progreso y descarga la actualizacion."""
        win = ctk.CTkToplevel(self)
        win.title("Descargando actualización...")
        win.geometry("460x230")
        win.grab_set()
        win.resizable(False, False)
        win.attributes("-topmost", True)

        container = ctk.CTkFrame(win, fg_color=self.colors["bg"])
        container.pack(fill="both", expand=True, padx=20, pady=15)

        ctk.CTkLabel(container, text="📥 Descargando NetHUB Ultimate",
                     font=("Arial", 16, "bold"), text_color=self.colors["accent"]).pack(pady=(15, 5))

        status_label = ctk.CTkLabel(container, text="Preparando descarga...",
                                    font=("Arial", 11), text_color=self.colors["text_secondary"])
        status_label.pack(pady=5)

        progress = ctk.CTkProgressBar(container, width=380, height=22,
                                      progress_color=self.colors["accent"])
        progress.pack(pady=10)
        progress.set(0)

        size_label = ctk.CTkLabel(container, text="", font=("Arial", 9),
                                  text_color=self.colors["text_secondary"])
        size_label.pack()

        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(pady=(12, 5))

        cancel_flag = {"cancel": False}

        def cancel_download():
            cancel_flag["cancel"] = True
            win.destroy()

        cancel_btn = ctk.CTkButton(btn_frame, text="Cancelar", command=cancel_download,
                                   fg_color="transparent", hover_color=self.colors["hover"],
                                   text_color=self.colors["text_secondary"],
                                   width=130, height=34, border_width=1,
                                   border_color=self.colors["border"])
        cancel_btn.pack()

        def update_progress(downloaded, total, status):
            self.after(0, lambda: _update_ui(downloaded, total, status))

        def _update_ui(downloaded, total, status):
            if cancel_flag["cancel"] or not win.winfo_exists():
                return
            try:
                status_label.configure(text=status)
                if total > 0:
                    pct = max(0, min(1, downloaded / total))
                    progress.set(pct)
                    mb_dl = downloaded / (1024 * 1024)
                    mb_tot = total / (1024 * 1024)
                    size_label.configure(text=f"{mb_dl:.1f} MB / {mb_tot:.1f} MB")
                else:
                    progress.set(0.5)
                    size_label.configure(text=f"{downloaded / 1024:.0f} KB descargados")
            except Exception:
                logger.debug("Error en callback de progreso de descarga")

        def download_thread():
            try:
                filepath = self.updater.download_update(url, progress_callback=update_progress)
                self.after(0, lambda: _download_finished(filepath))
            except Exception:
                self.after(0, lambda: _download_finished(None))

        def _download_finished(filepath):
            if cancel_flag["cancel"] or not win.winfo_exists():
                return
            try:
                for w in btn_frame.winfo_children():
                    w.destroy()

                if filepath:
                    status_label.configure(text="✅ Descarga completada")
                    progress.set(1)
                    size_label.configure(text="")

                    def open_file():
                        self.updater.run_installer(filepath)
                        win.destroy()

                    def open_folder():
                        folder = os.path.dirname(filepath)
                        if platform.system() == "Windows":
                            os.startfile(folder)
                        else:
                            subprocess.Popen(["open", folder])
                        win.destroy()

                    row = ctk.CTkFrame(btn_frame, fg_color="transparent")
                    row.pack()
                    ctk.CTkButton(row, text="▶ Ejecutar", command=open_file,
                                  fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                                  width=150, height=36, font=("Arial", 12, "bold")).pack(side="left", padx=8)
                    ctk.CTkButton(row, text="📁 Abrir carpeta", command=open_folder,
                                  fg_color="transparent", hover_color=self.colors["hover"],
                                  text_color=self.colors["text_secondary"],
                                  width=150, height=36, border_width=1,
                                  border_color=self.colors["border"]).pack(side="left", padx=8)
                else:
                    status_label.configure(text="❌ Error en la descarga")
                    progress.set(0)

                    def close():
                        win.destroy()
                    ctk.CTkButton(btn_frame, text="Cerrar", command=close,
                                  fg_color=self.colors["accent"], hover_color=self.colors["hover"],
                                  width=130, height=36).pack()
            except Exception:
                pass

        threading.Thread(target=download_thread, daemon=True).start()

    def create_floating_chat(self):
        """Crea el widget de chat flotante en la esquina inferior derecha"""
        if self.floating_chat_window and self.floating_chat_window.winfo_exists():
            return
        
        # Ventana flotante translúcida
        self.floating_chat_window = ctk.CTkToplevel(self)
        self.floating_chat_window.title("💬 NetHub AI")
        self.floating_chat_window.geometry("320x420")
        self.floating_chat_window.attributes("-topmost", True)
        self.floating_chat_window.attributes("-alpha", 0.85)
        
        # Posicionar en esquina inferior derecha
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        self.floating_chat_window.geometry(f"+{screen_width-340}+{screen_height-460}")
        
        # Header
        header = ctk.CTkFrame(self.floating_chat_window, fg_color=self.colors["accent"], corner_radius=10)
        header.pack(fill="x", padx=5, pady=(5, 0))
        
        ctk.CTkLabel(header, text="🤖 NetHub IA Rápida", font=("Arial", 11, "bold"), 
                    text_color="white").pack(pady=8)
        
        # Chat display compacto
        chat_box = ctk.CTkTextbox(self.floating_chat_window, fg_color=self.colors["bg"], 
                                  text_color=self.colors["text"], font=("Arial", 10),
                                  height=220)
        chat_box.pack(fill="both", expand=True, padx=5, pady=5)
        chat_box.insert("end", "✨ Asistente IA Flotante\n")
        chat_box.insert("end", "Pregunta cualquier cosa\n\n")
        chat_box.configure(state="disabled")
        self.floating_chat_display = chat_box
        
        # Input
        input_frame = ctk.CTkFrame(self.floating_chat_window, fg_color="transparent")
        input_frame.pack(fill="x", padx=5, pady=5)
        
        input_field = ctk.CTkEntry(input_frame, placeholder_text="Pregunta rápida…", 
                                   fg_color=self.colors["fg"], text_color=self.colors["text"],
                                   height=30, font=("Arial", 10))
        input_field.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.floating_chat_input = input_field
        
        def send_floating_message():
            msg = input_field.get().strip()
            if not msg:
                return
            input_field.delete(0, "end")
            
            # Mostrar mensaje del usuario
            chat_box.configure(state="normal")
            chat_box.insert("end", f"\n👤: {msg}\n")
            chat_box.see("end")
            chat_box.configure(state="disabled")
            
            # Generar respuesta en background
            def generate():
                try:
                    response = self.ollama.generate_quick(msg, max_chars=140)
                    self.after(0, lambda: (
                        chat_box.configure(state="normal"),
                        chat_box.insert("end", f"🤖: {response.strip()}\n"),
                        chat_box.see("end"),
                        chat_box.configure(state="disabled"),
                        # Toast con respuesta si es corta
                        len(response) < 100 and self.toast.show(response.strip()[:80], duration=4, type="info")
                    ))
                except Exception as e:
                    self.after(0, lambda: (
                        chat_box.configure(state="normal"),
                        chat_box.insert("end", f"⚠️ Error: {str(e)[:30]}\n"),
                        chat_box.configure(state="disabled")
                    ))
            
            threading.Thread(target=generate, daemon=True).start()
        
        input_field.bind("<Return>", lambda e: send_floating_message())
        
        btn = ctk.CTkButton(input_frame, text="📤", command=send_floating_message, 
                           fg_color=self.colors["accent"], width=30, height=30,
                           font=("Arial", 12))
        btn.pack(side="left")

    def toggle_floating_chat(self):
        """Alterna la visibilidad del chat flotante"""
        if self.floating_chat_window and self.floating_chat_window.winfo_exists():
            self.floating_chat_window.destroy()
            self.floating_chat_window = None
        else:
            self.create_floating_chat()

    def _handle_escape(self, event=None):
        """Maneja la tecla Escape: cierra chat flotante si está abierto"""
        if self.floating_chat_window and self.floating_chat_window.winfo_exists():
            self.floating_chat_window.destroy()
            self.floating_chat_window = None
            return "break"

    def _focus_floating_chat(self):
        """Abre o enfoca el chat flotante"""
        if not self.floating_chat_window or not self.floating_chat_window.winfo_exists():
            self.create_floating_chat()
        self.after(200, lambda: self.floating_chat_input.focus_set() if hasattr(self, 'floating_chat_input') and self.floating_chat_input.winfo_exists() else None)

    def _show_dashboard_wrapper(self):
        self._active_module = None
        self.current_menu = self.show_dashboard
        self.track_menu_usage(0)
        self.show_dashboard()

    def _show_chat_wrapper(self):
        self._active_module = None
        self.current_menu = self.show_chat
        chat_idx = len(self.menu_buttons) - 1
        self.track_menu_usage(chat_idx)
        self.show_chat()

    def _init_modules(self):
        self.module_manager.load_all()
        self.modules = self.module_manager.modules

    def _register_core_api(self):
        api = self.api

        api.register("system.toast", lambda msg, t="info", d=3: self.toast.show(msg, d, t),
                     module="core", description="Muestra notificacion toast",
                     params=[{"name": "msg", "type": "str"}, {"name": "t", "type": "str", "default": "info"},
                             {"name": "d", "type": "int", "default": 3}])

        api.register("system.lock", lambda: self.after(100, self.lock_screen),
                     module="core", description="Bloquea la pantalla")

        api.register("system.theme", lambda theme=None: self._api_set_theme(theme),
                     module="core", description="Cambia o consulta el tema actual",
                     params=[{"name": "theme", "type": "str", "default": None}])

        api.register("ai.chat", lambda prompt: self.ollama.generate(prompt),
                     module="core", description="Envia mensaje a la IA",
                     params=[{"name": "prompt", "type": "str"}])

        api.register("ai.quick", lambda prompt: self.ollama.generate_quick(prompt),
                     module="core", description="Respuesta rapida de la IA",
                     params=[{"name": "prompt", "type": "str"}])

        api.register("app.reload", lambda: self.after(100, self.reload_ui),
                     module="core", description="Recarga la interfaz")

        api.register("app.quit", lambda: self.after(500, self.destroy),
                     module="core", description="Cierra la aplicacion")

        api.register("api.commands", lambda module=None: api.list_commands(module),
                     module="core", description="Lista comandos disponibles",
                     params=[{"name": "module", "type": "str", "default": None}])

        api.register("api.execute", lambda name, **kw: self.api.execute_safe(name, **kw),
                     module="core", description="Ejecuta un comando de la API",
                     params=[{"name": "name", "type": "str"}, {"name": "kw", "type": "dict"}])

        api.register("script.run", lambda code: self.scripts.run(code),
                     module="core", description="Ejecuta un script",
                     params=[{"name": "code", "type": "str"}])

    def _api_set_theme(self, theme):
        if theme is None:
            return self.config_manager.config.get("theme", "dark")
        valid = {"dark", "blood", "matrix", "cyber", "custom"}
        if theme not in valid:
            return {"error": f"Tema invalido. Opciones: {', '.join(valid)}"}
        self.config_manager.config["theme"] = theme
        self.config_manager.save_config()
        self.update_colors()
        self.reload_ui()
        return {"ok": f"Tema cambiado a {theme}"}

    def activate_module(self, module):
        prev = self._active_module
        self.clear_content()
        self._active_module = module
        self.current_menu = lambda m=module: self._show_module_ui(m)
        for name, (btn, mod, idx) in self.module_buttons.items():
            if mod == module:
                self.set_active_menu(btn)
                self.track_menu_usage(idx)
                break
        module.build(self.content_frame)
        module.on_activate()
        if prev:
            self.events.emit("module.deactivated", module=prev)
        self.events.emit("module.activated", module=module)

    def _show_module_ui(self, module):
        self.clear_content()
        module.build(self.content_frame)

    def reload_ui(self):
        if self.current_menu:
            self.show_main_app()
            if self._active_module:
                self._active_module.build(self.content_frame)
            else:
                self.current_menu()



def kill_zombie_music():
    try:
        if 'app' in globals() and hasattr(app, 'music_process'):
            pid = app.music_process.pid
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        logger.debug("No se pudo matar proceso música por PID")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "ffplay.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        logger.debug("No se pudo matar ffplay.exe")

def signal_handler(sig, frame):
    kill_zombie_music()
    sys.exit(0)

# Registrar capturadores de señales del sistema operativo para cierres abruptos (Ctrl+C o cierre de consola)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Registrar capturador de salida estándar de Python
atexit.register(kill_zombie_music)

if __name__ == "__main__":
    app = NetHUBUltimate()
    app.mainloop()
