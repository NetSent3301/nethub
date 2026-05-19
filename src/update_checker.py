"""
Sistema de verificacion de actualizaciones para NetHUB Ultimate.
Consulta un archivo remoto y notifica al usuario si hay una version nueva.
"""
import json
import os
import platform
import tempfile
import webbrowser
from pathlib import Path

import requests

DEFAULT_UPDATE_URL = "https://raw.githubusercontent.com/NetSent3301/nethub-distro/main/version.json"


class UpdateChecker:
    CURRENT_VERSION = "2.1.0"

    def __init__(self, update_url=None):
        self.update_url = update_url or DEFAULT_UPDATE_URL
        self._download_progress = {"downloaded": 0, "total": 0, "status": ""}

    def set_update_url(self, url):
        self.update_url = url

    def get_update_url(self):
        return self.update_url

    def check_for_updates(self):
        """Consulta el servidor y devuelve info de la actualizacion."""
        result = {
            "available": False,
            "current_version": self.CURRENT_VERSION,
            "latest_version": self.CURRENT_VERSION,
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

        latest_version = data.get("version", self.CURRENT_VERSION)
        result["latest_version"] = latest_version
        result["changelog"] = data.get("changelog", [])
        result["download_url"] = data.get("download_url", "")
        result["message"] = data.get("message", "")
        result["mandatory"] = data.get("mandatory", False)

        if self._is_newer(latest_version, self.CURRENT_VERSION):
            result["available"] = True

            min_version = data.get("min_version")
            if min_version and not self._is_newer(self.CURRENT_VERSION, min_version):
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

    def download_update(self, url, progress_callback=None):
        """
        Descarga el archivo de actualizacion con reporte de progreso.
        progress_callback(downloaded, total, status) se llama durante la descarga.
        Retorna la ruta del archivo descargado o None si falla.
        """
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code != 200:
                if progress_callback:
                    progress_callback(0, 0, f"Error HTTP: {response.status_code}")
                return None

            total = int(response.headers.get("content-length", 0))
            downloaded = 0

            ext = ".zip" if "zip" in url else ".exe" if "exe" in url else ".bin"
            filename = f"NetHUB_Ultimate_update{ext}"

            download_dir = Path(tempfile.gettempdir()) / "NetHUB_Updates"
            download_dir.mkdir(parents=True, exist_ok=True)
            filepath = download_dir / filename

            if progress_callback:
                progress_callback(0, total, "Iniciando descarga...")

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total > 0:
                            pct = int(downloaded / total * 100)
                            progress_callback(downloaded, total, f"Descargando... {pct}%")

            if progress_callback:
                progress_callback(downloaded, total, "Descarga completada")

            return str(filepath)

        except requests.exceptions.Timeout:
            if progress_callback:
                progress_callback(0, 0, "Timeout en la descarga")
        except requests.exceptions.ConnectionError:
            if progress_callback:
                progress_callback(0, 0, "Error de conexion")
        except Exception as e:
            if progress_callback:
                progress_callback(0, 0, f"Error: {str(e)}")
        return None

    def run_installer(self, filepath):
        """Ejecuta el instalador/archivo descargado."""
        if not filepath or not os.path.exists(filepath):
            return False
        try:
            system = platform.system()
            if system == "Windows":
                os.startfile(filepath)
            elif system == "Darwin":
                import subprocess
                subprocess.Popen(["open", filepath])
            else:
                import subprocess
                subprocess.Popen(["xdg-open", filepath])
            return True
        except Exception:
            return False
