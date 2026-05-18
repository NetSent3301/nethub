"""
Modulo central de logica de NetHUB Ultimate.
Contiene las clases que no dependen de la interfaz grafica.
"""
import os
import json
import hashlib
import bcrypt
import datetime
import requests
import re

# Esquemas de color premium
COLOR_SCHEMES = {
    "dark": {
        "bg": "#0a0a0a", "fg": "#1a1a1a", "accent": "#2a6a8a", "accent_light": "#3a8aaa",
        "text": "#e0e0e0", "text_secondary": "#a0a0a0", "hover": "#2a4a5a",
        "sidebar": "#0a0a0a", "active": "#2a6a8a", "border": "#2a2a2a",
        "success": "#2a6a3a", "error": "#8a2a2a", "warning": "#8a6a2a"
    },
    "blood": {
        "bg": "#1a0505", "fg": "#2a0a0a", "accent": "#8a1a1a", "accent_light": "#aa2a2a",
        "text": "#d4a0a0", "text_secondary": "#b08080", "hover": "#5a1010",
        "sidebar": "#1a0505", "active": "#8a1a1a", "border": "#3a1010",
        "success": "#2a4a2a", "error": "#aa2a2a", "warning": "#aa8a2a"
    },
    "matrix": {
        "bg": "#0a1a0a", "fg": "#0f2a0f", "accent": "#2aaa2a", "accent_light": "#3acc3a",
        "text": "#a0d4a0", "text_secondary": "#80b080", "hover": "#1a4a1a",
        "sidebar": "#0a1a0a", "active": "#2aaa2a", "border": "#1a3a1a",
        "success": "#2a8a2a", "error": "#aa2a2a", "warning": "#aaaa2a"
    },
    "cyber": {
        "bg": "#0a0a1a", "fg": "#0f0f2a", "accent": "#aa2aaa", "accent_light": "#cc3acc",
        "text": "#d4a0d4", "text_secondary": "#b080b0", "hover": "#4a1a4a",
        "sidebar": "#0a0a1a", "active": "#aa2aaa", "border": "#2a1a3a",
        "success": "#2a6a2a", "error": "#aa2a2a", "warning": "#aa8a2a"
    }
}

USERS_FILE = "users.json"
CONFIG_FILE = "config.json"


class UserManager:
    def __init__(self, users_file=None):
        self.users_file = users_file or USERS_FILE
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r') as f:
                self.users = json.load(f)

    def save_users(self):
        with open(self.users_file, 'w') as f:
            json.dump(self.users, f)

    def register(self, username, password, avatar_path, email=""):
        if username in self.users:
            return False, "Usuario ya existe"
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        self.users[username] = {
            "password": hashed,
            "avatar": avatar_path,
            "display_name": username,
            "email": email,
            "created": __import__("time").time(),
            "last_login": None,
            "failed_attempts": 0
        }
        self.save_users()
        return True, "Registro exitoso"

    def login(self, username, password):
        user = self.users.get(username)
        if not user:
            return False, "Usuario no existe"
        if user.get("failed_attempts", 0) >= 5:
            return False, "Cuenta bloqueada por intentos fallidos"

        stored_hash = user.get("password", "")

        if stored_hash.startswith("$2"):
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                user["last_login"] = __import__("time").time()
                user["failed_attempts"] = 0
                self.save_users()
                return True, user.get("avatar", "")
        else:
            legacy_hash = hashlib.sha256(password.encode()).hexdigest()
            if stored_hash == legacy_hash:
                salt = bcrypt.gensalt(rounds=12)
                user["password"] = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
                user["last_login"] = __import__("time").time()
                user["failed_attempts"] = 0
                self.save_users()
                return True, user.get("avatar", "")

        user["failed_attempts"] = user.get("failed_attempts", 0) + 1
        self.save_users()
        remaining = 5 - user["failed_attempts"]
        return False, f"Contraseña incorrecta ({remaining} intentos restantes)"

    def login_google(self, email, name="", avatar_url="", avatar_local=""):
        if email not in self.users:
            self.users[email] = {
                "password": "",
                "avatar": avatar_local,
                "auth_provider": "google",
                "display_name": name,
                "email": email,
                "google_avatar": avatar_url,
                "created": __import__("time").time(),
                "last_login": None,
                "failed_attempts": 0,
                "google_linked": __import__("time").time()
            }
        else:
            was_local = self.users[email].get("auth_provider") != "google"
            self.users[email]["auth_provider"] = "google"
            self.users[email]["display_name"] = name or self.users[email].get("display_name", "")
            self.users[email]["google_avatar"] = avatar_url or self.users[email].get("google_avatar", "")
            if avatar_local:
                self.users[email]["avatar"] = avatar_local
            if was_local:
                self.users[email]["google_linked"] = __import__("time").time()
        self.save_users()
        return True, "Login con Google exitoso"

    def rename_username(self, old_username, new_username):
        if not new_username or new_username.strip() == "":
            return False, "Nombre inválido"
        if new_username in self.users:
            return False, "Nombre ya registrado"
        self.users[new_username] = self.users.pop(old_username)
        self.save_users()
        return True, "Nombre actualizado"

    def change_password(self, username, new_password):
        if not new_password or len(new_password) < 4:
            return False, "Mínimo 4 caracteres"
        salt = bcrypt.gensalt(rounds=12)
        self.users[username]["password"] = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')
        self.save_users()
        return True, "Contraseña actualizada"


class ConfigManager:
    def __init__(self, config_file=None):
        self.config_file = config_file or CONFIG_FILE
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                try:
                    cfg = json.load(f)
                    if "theme" not in cfg: cfg["theme"] = "dark"
                    if "custom_colors" not in cfg: cfg["custom_colors"] = None
                    if "appearance_mode" not in cfg: cfg["appearance_mode"] = "System"
                    if "sound_effects" not in cfg: cfg["sound_effects"] = True
                    if "dashboard_layout" not in cfg: cfg["dashboard_layout"] = None
                    return cfg
                except Exception:
                    pass
        return {"theme": "dark", "custom_colors": None, "appearance_mode": "System", "sound_effects": True, "dashboard_layout": None}

    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f)

    def _hex_to_rgb(self, color):
        color = str(color or "#000000").strip()
        if not color.startswith("#"):
            return (0, 0, 0)
        color = color[1:]
        if len(color) == 3:
            color = "".join(ch * 2 for ch in color)
        try:
            return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        except:
            return (0, 0, 0)

    def _rgb_to_hex(self, rgb):
        r, g, b = [max(0, min(255, int(v))) for v in rgb]
        return f"#{r:02x}{g:02x}{b:02x}"

    def _luminance(self, color):
        r, g, b = self._hex_to_rgb(color)
        channels = []
        for value in (r, g, b):
            value = value / 255
            channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]

    def _mix(self, color, target, amount):
        rgb = self._hex_to_rgb(color)
        target_rgb = self._hex_to_rgb(target)
        return self._rgb_to_hex(tuple(rgb[i] + (target_rgb[i] - rgb[i]) * amount for i in range(3)))

    def _readable_on(self, color):
        return "#111111" if self._luminance(color) > 0.55 else "#ffffff"

    def _contrast_ratio(self, a, b):
        lum_a = self._luminance(a)
        lum_b = self._luminance(b)
        high, low = max(lum_a, lum_b), min(lum_a, lum_b)
        return (high + 0.05) / (low + 0.05)

    def _with_contrast_helpers(self, colors):
        colors = colors.copy()
        colors["on_bg"] = self._readable_on(colors.get("bg", "#000000"))
        colors["on_fg"] = self._readable_on(colors.get("fg", "#000000"))
        colors["on_hover"] = self._readable_on(colors.get("hover", colors.get("fg", "#000000")))
        colors["on_accent"] = self._readable_on(colors.get("accent", "#2a6a8a"))
        colors["on_active"] = self._readable_on(colors.get("active", colors.get("accent", "#2a6a8a")))
        return colors

    def _ensure_accent_contrast(self, colors):
        colors = colors.copy()
        bg = colors.get("bg", "#000000")
        fg = colors.get("fg", bg)
        sidebar = colors.get("sidebar", bg)
        accent = colors.get("accent", "#2a6a8a")
        min_contrast = min(
            self._contrast_ratio(accent, bg),
            self._contrast_ratio(accent, fg),
            self._contrast_ratio(accent, sidebar)
        )
        if min_contrast < 3:
            target = "#ffffff" if max(self._luminance(bg), self._luminance(fg), self._luminance(sidebar)) < 0.45 else "#000000"
            for amount in (0.45, 0.6, 0.75, 0.9):
                candidate = self._mix(accent, target, amount)
                candidate_contrast = min(
                    self._contrast_ratio(candidate, bg),
                    self._contrast_ratio(candidate, fg),
                    self._contrast_ratio(candidate, sidebar)
                )
                if candidate_contrast >= 3 or amount == 0.9:
                    colors["accent"] = candidate
                    colors["active"] = candidate
                    colors["accent_light"] = self._mix(candidate, "#ffffff" if target == "#000000" else "#000000", 0.18)
                    break
        return colors

    def _with_accessible_text(self, colors):
        colors = colors.copy()
        bg_lum = self._luminance(colors.get("bg", "#000000"))
        fg_lum = self._luminance(colors.get("fg", colors.get("bg", "#000000")))
        surface_lum = max(bg_lum, fg_lum)

        if surface_lum > 0.55:
            colors["text"] = "#161616"
            colors["text_secondary"] = "#444444"
            colors["border"] = self._mix(colors.get("fg", "#ffffff"), "#000000", 0.22)
            colors["hover"] = self._mix(colors.get("fg", "#ffffff"), "#000000", 0.12)
            colors["sidebar"] = self._mix(colors.get("bg", "#ffffff"), "#000000", 0.06)
        elif surface_lum > 0.32:
            colors["text"] = "#101010"
            colors["text_secondary"] = "#383838"
            colors["border"] = self._mix(colors.get("fg", "#cccccc"), "#000000", 0.30)
        else:
            colors["text"] = "#e8e8e8"
            colors["text_secondary"] = "#b5b5b5"

        colors = self._ensure_accent_contrast(colors)
        return self._with_contrast_helpers(colors)

    def get_colors(self):
        if self.config["theme"] == "custom" and self.config.get("custom_colors"):
            return self._with_accessible_text(self.config["custom_colors"])
        return self._with_contrast_helpers(COLOR_SCHEMES.get(self.config["theme"], COLOR_SCHEMES["dark"]))


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
            return "Error: Ollama no esta corriendo. Inicia 'ollama serve'"

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
            chunk_callback("Error: Ollama no esta corriendo. Inicia 'ollama serve'", True)
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
        import io
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

        import math, time, random, json as _json, re as _re
        SAFE_GLOBALS = {
            "__builtins__": SAFE_BUILTINS,
            "time": time, "math": math,
            "random": random, "json": _json, "re": _re,
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
