"""
Motor de scripting para NetHUB Ultimate.
Permite ejecutar codigo Python definido por el usuario con acceso a la API y eventos.
"""
import io
import textwrap
from contextlib import redirect_stdout, redirect_stderr
from .logger import get_logger

logger = get_logger("scripting")


class ScriptEngine:
    def __init__(self, api=None, events=None):
        self.api = api
        self.events = events
        self._globals = {}
        self._reset_globals()

    def _reset_globals(self):
        safe_builtins = {
            "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
            "bytes": bytes, "chr": chr, "dict": dict, "divmod": divmod,
            "enumerate": enumerate, "filter": filter, "float": float,
            "format": format, "frozenset": frozenset, "hash": hash,
            "hex": hex, "id": id, "int": int, "isinstance": isinstance,
            "issubclass": issubclass, "iter": iter, "len": len, "list": list,
            "map": map, "max": max, "min": min, "next": next, "oct": oct,
            "ord": ord, "pow": pow, "print": print, "range": range,
            "repr": repr, "reversed": reversed, "round": round, "set": set,
            "slice": slice, "sorted": sorted, "str": str, "sum": sum,
            "tuple": tuple, "type": type, "zip": zip,
            "True": True, "False": False, "None": None,
        }
        self._globals = {
            "__builtins__": safe_builtins,
            "api": self.api,
            "events": self.events,
        }

    def run(self, code, context=None):
        f_out = io.StringIO()
        f_err = io.StringIO()

        local_context = dict(self._globals)
        if context:
            local_context.update(context)

        try:
            with redirect_stdout(f_out), redirect_stderr(f_err):
                exec(code, local_context)
            output = f_out.getvalue()
            error = f_err.getvalue()
            result = local_context.get("result", None)
            return {"ok": True, "output": output, "error": error, "result": result}
        except Exception as e:
            error = f_err.getvalue()
            return {"ok": False, "output": f_out.getvalue(), "error": str(e), "trace": error}

    def run_file(self, path, context=None):
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        return self.run(code, context)

    def register_script(self, name, code):
        path = f"scripts/{name}.py"
        import os
        os.makedirs("scripts", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(code))
        logger.info("Script guardado: %s", path)
        return path

    def list_scripts(self):
        import os
        import glob
        scripts = []
        for f in glob.glob("scripts/*.py"):
            scripts.append({"name": os.path.splitext(os.path.basename(f))[0], "path": f})
        return scripts
