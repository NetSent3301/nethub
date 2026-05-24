import os
import sys
import json
import importlib.util
import inspect
from pathlib import Path

from core.logger import get_logger, log_exception

logger = get_logger("module_manager")


def _is_frozen():
    return getattr(sys, "frozen", False)


def _get_exe_dir():
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent.parent


class ModuleManager:
    CUSTOM_MODULES_DIR = os.path.join(os.path.dirname(__file__), "custom")

    def __init__(self, app):
        self.app = app
        self._modules = {}
        self._loaded_files = {}
        self._plugins_dir = self._resolve_plugins_dir()

    def _resolve_plugins_dir(self):
        if _is_frozen():
            plugins = _get_exe_dir() / "plugins"
        else:
            plugins = _get_exe_dir() / "plugins"
        plugins.mkdir(parents=True, exist_ok=True)
        return str(plugins)

    def get_plugins_dir(self):
        return self._plugins_dir

    @property
    def modules(self):
        return self._modules

    BUILTIN_MODULES = [
        "code_module", "crypto_module", "files_module", "hacking_module",
        "marketplace_module", "monitor_module", "network_module", "notas_module", 
        "osint_module", "sandbox_module", "search_module", "system_module", 
        "tasks_module", "utils_module", "music_module",
    ]

    def discover_builtin(self):
        if _is_frozen():
            for mod_name in self.BUILTIN_MODULES:
                self._load_builtin_module(mod_name)
        else:
            dir_path = os.path.dirname(__file__)
            for fname in sorted(os.listdir(dir_path)):
                if not fname.endswith("_module.py") or fname.startswith("_"):
                    continue
                self._load_module_file(os.path.join(dir_path, fname), fname)

    def _load_builtin_module(self, mod_name):
        full_name = f"modules.{mod_name}"
        if full_name in self._loaded_files:
            return
        try:
            module = importlib.import_module(full_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name in ("BaseModule", "ToolFrameContainer", "AnimatedGraph"):
                    continue
                if not hasattr(obj, "name") or not hasattr(obj, "icon"):
                    continue
                if not hasattr(obj, "build") or not callable(getattr(obj, "build", None)):
                    continue
                self._register_class(obj, f"{mod_name}.py")
            self._loaded_files[full_name] = module
        except Exception:
            logger.error("Error cargando módulo %s", mod_name, exc_info=True)

    def discover_custom(self):
        self._discover_dir(self.CUSTOM_MODULES_DIR, custom=True)
        self._discover_dir(self._plugins_dir, custom=True, plugin=True)

    def _discover_dir(self, directory, custom=False, plugin=False):
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            return

        for entry in sorted(os.listdir(directory)):
            entry_path = os.path.join(directory, entry)

            if os.path.isfile(entry_path) and entry.endswith("_module.py"):
                self._load_module_file(entry_path, entry, custom=custom)
            elif os.path.isdir(entry_path):
                plugin_json = os.path.join(entry_path, "plugin.json")
                main_py = os.path.join(entry_path, "main.py")
                if os.path.isfile(plugin_json) and os.path.isfile(main_py):
                    self._load_plugin_folder(entry_path, entry, custom=custom)

    def _load_plugin_folder(self, folder_path, folder_name, custom=False):
        if folder_path in self._loaded_files:
            return

        json_path = os.path.join(folder_path, "plugin.json")
        main_path = os.path.join(folder_path, "main.py")

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception:
            logger.warning("Error leyendo plugin.json en %s", folder_name, exc_info=True)
            return

        mod_name = f"plugin_{folder_name}"
        try:
            spec = importlib.util.spec_from_file_location(mod_name, main_path)
            if spec is None or spec.loader is None:
                logger.warning("No se pudo cargar spec: %s", folder_name)
                return

            module = importlib.util.module_from_spec(spec)
            module.__package__ = "modules.plugins"
            if custom:
                sys.modules[f"modules.plugins.{mod_name}"] = module

            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name in ("BaseModule", "ToolFrameContainer", "AnimatedGraph"):
                    continue
                if not hasattr(obj, "name") or not hasattr(obj, "icon"):
                    continue
                if not hasattr(obj, "build") or not callable(getattr(obj, "build", None)):
                    continue

                if metadata.get("name"):
                    obj.name = metadata["name"]
                if metadata.get("icon"):
                    obj.icon = metadata["icon"]
                if metadata.get("description"):
                    obj.description = metadata["description"]

                self._register_class(obj, folder_name, custom=custom)
                instance = self._modules.get(obj.name)
                if instance:
                    instance._plugin_metadata = metadata
                    instance._plugin_folder = folder_path

            self._loaded_files[folder_path] = module

        except Exception:
            logger.error("Error cargando plugin %s", folder_name, exc_info=True)

    def _load_module_file(self, filepath, filename, custom=False):
        if filepath in self._loaded_files:
            return

        mod_name = filename[:-3]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, filepath)
            if spec is None or spec.loader is None:
                logger.warning("No se pudo cargar spec: %s", filename)
                return

            module = importlib.util.module_from_spec(spec)

            if custom:
                sys.modules[f"modules.custom.{mod_name}"] = module
                module.__package__ = "modules.custom"
            else:
                sys.modules[f"modules.{mod_name}"] = module
                module.__package__ = "modules"

            spec.loader.exec_module(module)

            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name in ("BaseModule", "ToolFrameContainer", "AnimatedGraph"):
                    continue
                if not hasattr(obj, "name") or not hasattr(obj, "icon"):
                    continue
                if not hasattr(obj, "build") or not callable(getattr(obj, "build", None)):
                    continue
                self._register_class(obj, filename, custom=custom)

            self._loaded_files[filepath] = module

        except Exception as e:
            logger.error("Error cargando módulo %s", filename, exc_info=True)

    def _register_class(self, cls, source_file, custom=False):
        if not hasattr(cls, "name") or not cls.name:
            return

        if cls.name in self._modules:
            return

        try:
            instance = cls(self.app)
            instance._is_custom = custom

            if not hasattr(instance, "build") or not callable(instance.build):
                return

            self._modules[cls.name] = instance

            api = getattr(self.app, "api", None)
            if api and getattr(instance, "api_commands", None):
                api.register_module(instance)

            events = getattr(self.app, "events", None)
            if events and getattr(instance, "event_map", None):
                events.subscribe_module(instance, instance.event_map)

            if hasattr(instance, "on_api_registered"):
                instance.on_api_registered(api)

        except Exception:
            logger.error("Error instanciando %s", cls.__name__, exc_info=True)

    def register(self, cls):
        if not inspect.isclass(cls):
            raise TypeError(f"Se esperaba una clase, se recibió {type(cls)}")
        if not hasattr(cls, "name") or not hasattr(cls, "build"):
            raise TypeError(f"{cls.__name__} debe tener atributos 'name' y 'build()'")
        self._register_class(cls, "runtime")
        return cls.name in self._modules

    def unregister(self, module_name):
        if module_name in self._modules:
            mod = self._modules.pop(module_name)
            if hasattr(mod, "on_deactivate"):
                try:
                    mod.on_deactivate()
                except Exception:
                    logger.debug("Error en on_deactivate de %s", module_name)
            return True
        return False

    def reload_custom(self):
        custom_modules = {
            name: mod for name, mod in self._modules.items()
            if getattr(mod, "_is_custom", False)
        }
        for name in custom_modules:
            self.unregister(name)

        self._loaded_files = {
            path: mod for path, mod in self._loaded_files.items()
            if not path.startswith(self.CUSTOM_MODULES_DIR) and not path.startswith(self._plugins_dir)
        }

        self.discover_custom()
        return len(self._modules)

    def get_info(self):
        info = []
        for name, mod in self._modules.items():
            entry = {
                "name": name,
                "icon": getattr(mod, "icon", ""),
                "description": getattr(mod, "description", ""),
                "custom": getattr(mod, "_is_custom", False),
                "class": mod.__class__.__name__,
            }
            metadata = getattr(mod, "_plugin_metadata", None)
            if metadata:
                entry["version"] = metadata.get("version", "")
                entry["author"] = metadata.get("author", "")
                entry["_is_plugin"] = True
            else:
                entry["version"] = ""
                entry["author"] = ""
                entry["_is_plugin"] = False
            info.append(entry)
        return info

    def load_all(self):
        self.discover_builtin()
        self.discover_custom()

    @staticmethod
    def create_plugin_template(plugins_dir, name):
        safe = "".join(c for c in name if c.isalnum() or c in " _-").strip().replace(" ", "_")
        if not safe:
            return None

        folder = Path(plugins_dir) / safe
        if folder.exists():
            return None
        folder.mkdir(parents=True)

        plugin_json = {
            "name": name,
            "icon": "🧩",
            "description": "Mi plugin personalizado",
            "version": "1.0.0",
            "author": "Desconocido"
        }

        main_py = f'''"""
Plugin: {name}
Generado automaticamente por NetHUB Ultimate
"""
import customtkinter as ctk

from modules.base_module import BaseModule


class {safe}Module(BaseModule):
    name = "{name}"
    icon = "🧩"
    description = "Mi plugin personalizado"

    def build(self, parent):
        colors = self.colors
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        header = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=15)
        header.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header,
            text=f"{{self.icon}} {{self.name.upper()}}",
            font=("Arial", 22, "bold"),
            text_color=colors["text"],
        ).pack(pady=20, padx=20)

        content = ctk.CTkFrame(frame, fg_color=colors["fg"], corner_radius=12)
        content.pack(fill="both", expand=True)

        ctk.CTkLabel(
            content,
            text="¡Tu plugin funciona!",
            font=("Arial", 14),
            text_color=colors["text"],
        ).pack(pady=30)
'''

        with open(os.path.join(folder, "plugin.json"), "w", encoding="utf-8") as f:
            json.dump(plugin_json, f, indent=2, ensure_ascii=False)

        with open(os.path.join(folder, "main.py"), "w", encoding="utf-8") as f:
            f.write(main_py)

        return str(folder)
