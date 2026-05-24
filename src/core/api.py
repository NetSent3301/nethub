"""
API Registry unificado para NetHUB Ultimate.
Expone funciones del programa como comandos invocables por scripting, otros modulos, o REST.
"""
from .logger import get_logger

logger = get_logger("api")


class Command:
    def __init__(self, name, fn, module="", description="", params=None):
        self.name = name
        self.fn = fn
        self.module = module
        self.description = description or fn.__doc__ or ""
        self.params = params or []

    def __call__(self, **kwargs):
        return self.fn(**kwargs)

    def to_dict(self):
        return {
            "name": self.name,
            "module": self.module,
            "description": self.description,
            "params": self.params,
        }


class API:
    def __init__(self, app=None):
        self.app = app
        self._commands = {}

    def register(self, name, fn, module="", description="", params=None):
        if name in self._commands:
            logger.warning("Comando '%s' ya registrado, sobrescribiendo", name)
        self._commands[name] = Command(name, fn, module, description, params)
        logger.debug("Comando registrado: %s [%s]", name, module)

    def register_module(self, module_instance):
        mod_name = module_instance.__class__.__name__
        commands = getattr(module_instance, "api_commands", None)
        if commands is None:
            return
        for cmd_name, cmd_def in commands.items():
            full_name = f"{mod_name}.{cmd_name}" if "." not in cmd_name else cmd_name
            fn = cmd_def if callable(cmd_def) else cmd_def.get("fn")
            desc = cmd_def.get("description", "") if not callable(cmd_def) else ""
            params = cmd_def.get("params", []) if not callable(cmd_def) else []
            api_name = cmd_def.get("name", full_name) if not callable(cmd_def) else full_name
            self.register(api_name, fn, module=mod_name, description=desc, params=params)

    def execute(self, name, **params):
        cmd = self._commands.get(name)
        if not cmd:
            raise KeyError(f"Comando no encontrado: {name}")
        logger.debug("Ejecutando comando: %s con params=%s", name, params)
        return cmd(**params)

    def execute_safe(self, name, **params):
        try:
            return self.execute(name, **params)
        except KeyError as e:
            return {"error": str(e)}
        except Exception as e:
            logger.error("Error ejecutando '%s': %s", name, e, exc_info=True)
            return {"error": str(e)}

    def list_commands(self, module=None):
        if module:
            return {n: c.to_dict() for n, c in self._commands.items() if c.module == module}
        return {n: c.to_dict() for n, c in self._commands.items()}

    def discover(self, search=""):
        results = []
        for name, cmd in self._commands.items():
            if search.lower() in name.lower() or search.lower() in cmd.description.lower():
                results.append(cmd.to_dict())
        return results

    @property
    def count(self):
        return len(self._commands)
