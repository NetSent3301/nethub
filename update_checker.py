"""
Sistema de verificacion de actualizaciones para NetHUB Ultimate.
Consulta un archivo remoto y notifica al usuario si hay una version nueva.
"""
import json
import requests
import os
import webbrowser

CURRENT_VERSION = "2.0.0"
DEFAULT_UPDATE_URL = "https://raw.githubusercontent.com/NetSent3301/nethub/main/version.json"


class UpdateChecker:
    def __init__(self, update_url=None):
        self.update_url = update_url or DEFAULT_UPDATE_URL
        self.update_url_file = "update_url.txt"
        self._load_custom_url()

    def _load_custom_url(self):
        if os.path.exists(self.update_url_file):
            try:
                with open(self.update_url_file, "r") as f:
                    self.update_url = f.read().strip()
            except:
                pass

    def set_update_url(self, url):
        self.update_url = url
        try:
            with open(self.update_url_file, "w") as f:
                f.write(url)
        except:
            pass

    def get_update_url(self):
        return self.update_url

    def check_for_updates(self):
        """Consulta el servidor y devuelve info de la actualizacion."""
        result = {
            "available": False,
            "current_version": CURRENT_VERSION,
            "latest_version": CURRENT_VERSION,
            "changelog": [],
            "download_url": "",
            "message": "",
            "mandatory": False,
            "error": None,
        }

        if not self.update_url or not self.update_url.startswith("http"):
            result["error"] = "URL de actualizacion no configurada"
            return result

        try:
            response = requests.get(self.update_url, timeout=8)
            if response.status_code != 200:
                result["error"] = f"Error HTTP: {response.status_code}"
                return result

            data = response.json()
        except requests.exceptions.Timeout:
            result["error"] = "Timeout al consultar actualizaciones"
            return result
        except requests.exceptions.ConnectionError:
            result["error"] = "Sin conexion de red"
            return result
        except json.JSONDecodeError:
            result["error"] = "Respuesta invalida del servidor"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

        latest_version = data.get("version", CURRENT_VERSION)
        result["latest_version"] = latest_version
        result["changelog"] = data.get("changelog", [])
        result["download_url"] = data.get("download_url", "")
        result["message"] = data.get("message", "")
        result["mandatory"] = data.get("mandatory", False)

        if self._is_newer(latest_version, CURRENT_VERSION):
            result["available"] = True

            min_version = data.get("min_version")
            if min_version and not self._is_newer(CURRENT_VERSION, min_version):
                result["mandatory"] = True
                result["message"] = "Actualizacion obligatoria. Tu version ya no es compatible."

        return result

    def _is_newer(self, version_a, version_b):
        """Compara dos versiones. Devuelve True si A es mas nueva que B."""
        try:
            parts_a = [int(x) for x in version_a.split(".")]
            parts_b = [int(x) for x in version_b.split(".")]

            while len(parts_a) < 3:
                parts_a.append(0)
            while len(parts_b) < 3:
                parts_b.append(0)

            return parts_a > parts_b
        except:
            return False

    def open_download(self, url=None):
        """Abre el enlace de descarga en el navegador."""
        download_url = url or ""
        if not download_url:
            return False
        try:
            webbrowser.open(download_url)
            return True
        except:
            return False
