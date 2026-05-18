import os
import sys
import importlib.util
import inspect


class ModuleManager:
    """Gestiona el ciclo de vida de módulos: descubrimiento, registro, validación y recarga."""

    CUSTOM_MODULES_DIR = os.path.join(os.path.dirname(__file__), "custom")

    def __init__(self, app):
        self.app = app
        self._modules = {}
        self._loaded_files = {}

    @property
    def modules(self):
        return self._modules

    def discover_builtin(self):
        """Descubre módulos oficiales en la carpeta modules/."""
        dir_path = os.path.dirname(__file__)
        for fname in sorted(os.listdir(dir_path)):
            if not fname.endswith("_module.py") or fname.startswith("_"):
                continue
            self._load_module_file(os.path.join(dir_path, fname), fname)

    def discover_custom(self):
        """Descubre módulos personalizados en modules/custom/."""
        if not os.path.exists(self.CUSTOM_MODULES_DIR):
            os.makedirs(self.CUSTOM_MODULES_DIR, exist_ok=True)
        for fname in sorted(os.listdir(self.CUSTOM_MODULES_DIR)):
            if not fname.endswith("_module.py") or fname.startswith("_"):
                continue
            filepath = os.path.join(self.CUSTOM_MODULES_DIR, fname)
            self._load_module_file(filepath, fname, custom=True)

    def _load_module_file(self, filepath, filename, custom=False):
        """Carga un archivo .py y registra las clases que heredan de BaseModule."""
        if filepath in self._loaded_files:
            return

        mod_name = filename[:-3]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, filepath)
            if spec is None or spec.loader is None:
                print(f"[ModuleManager] No se pudo cargar spec: {filename}")
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
            print(f"[ModuleManager] Error cargando {filename}: {e}")
            import traceback
            traceback.print_exc()

    def _register_class(self, cls, source_file, custom=False):
        """Valida e instancia una clase de módulo."""
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

        except Exception as e:
            print(f"[ModuleManager] Error instanciando {cls.__name__}: {e}")

    def register(self, cls):
        """Registra manualmente una clase de módulo en runtime."""
        if not inspect.isclass(cls):
            raise TypeError(f"Se esperaba una clase, se recibió {type(cls)}")
        if not hasattr(cls, "name") or not hasattr(cls, "build"):
            raise TypeError(f"{cls.__name__} debe tener atributos 'name' y 'build()'")
        self._register_class(cls, "runtime")
        return cls.name in self._modules

    def unregister(self, module_name):
        """Desregistra un módulo por nombre."""
        if module_name in self._modules:
            mod = self._modules.pop(module_name)
            if hasattr(mod, "on_deactivate"):
                try:
                    mod.on_deactivate()
                except:
                    pass
            print(f"[ModuleManager] - Módulo desregistrado: {module_name}")
            return True
        return False

    def reload_custom(self):
        """Recarga todos los módulos custom (útil para desarrollo en caliente)."""
        custom_modules = {
            name: mod for name, mod in self._modules.items()
            if getattr(mod, "_is_custom", False)
        }
        for name in custom_modules:
            self.unregister(name)

        self._loaded_files = {
            path: mod for path, mod in self._loaded_files.items()
            if not path.startswith(self.CUSTOM_MODULES_DIR)
        }

        self.discover_custom()
        return len(self._modules) - len(custom_modules) + len(self._modules)

    def get_info(self):
        """Devuelve información de todos los módulos cargados."""
        info = []
        for name, mod in self._modules.items():
            info.append({
                "name": name,
                "icon": getattr(mod, "icon", ""),
                "description": getattr(mod, "description", ""),
                "custom": getattr(mod, "_is_custom", False),
                "class": mod.__class__.__name__,
            })
        return info

    def load_all(self):
        """Carga todos los módulos (built-in + custom)."""
        self.discover_builtin()
        self.discover_custom()
