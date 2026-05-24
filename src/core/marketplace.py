"""
Gestor del Marketplace de Plugins para NetHUB
Descarga y gestiona plugins desde repositorio GitHub
"""

import os
import json
import requests
import shutil
import zipfile
import io
import threading
from pathlib import Path
from typing import Dict, List, Callable, Optional

from core.logger import get_logger

logger = get_logger("marketplace")


class MarketplaceManager:
    """Gestor del marketplace de plugins"""

    # URL del repositorio GitHub donde están los plugins
    # Formato esperado: owner/repo con rama main
    GITHUB_REPO = "NetSent3301/nethub-marketplace"
    GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
    CATALOG_URL = f"{GITHUB_RAW_URL}/catalog.json"

    def __init__(self, plugins_dir: str):
        """
        Args:
            plugins_dir: Ruta a la carpeta de plugins
        """
        self.plugins_dir = plugins_dir
        self.cache_dir = os.path.join(os.path.dirname(plugins_dir), "marketplace_cache")
        os.makedirs(self.cache_dir, exist_ok=True)

        self.catalog = {}
        self.installed_plugins = {}
        self._load_catalog()
        self._scan_installed()

    def _load_catalog(self):
        """Descarga o carga desde caché el catálogo de plugins"""
        cache_file = os.path.join(self.cache_dir, "catalog.json")

        # Intentar descargar
        try:
            response = requests.get(self.CATALOG_URL, timeout=5)
            if response.status_code == 200:
                self.catalog = response.json()
                # Guardar en caché
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.catalog, f, indent=2)
                logger.info("Catálogo descargado desde GitHub")
                return
        except Exception as e:
            logger.warning(f"No se pudo descargar catálogo: {e}")

        # Usar caché si existe
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    self.catalog = json.load(f)
                logger.info("Catálogo cargado desde caché")
            except Exception as e:
                logger.error(f"Error cargando caché: {e}")
                self.catalog = {}

    def _scan_installed(self):
        """Escanea plugins instalados"""
        self.installed_plugins = {}
        
        if not os.path.exists(self.plugins_dir):
            return

        for entry in os.listdir(self.plugins_dir):
            plugin_path = os.path.join(self.plugins_dir, entry)
            if not os.path.isdir(plugin_path):
                continue

            json_path = os.path.join(plugin_path, "plugin.json")
            if not os.path.exists(json_path):
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                    plugin_id = metadata.get("id", entry)
                    self.installed_plugins[plugin_id] = {
                        "path": plugin_path,
                        "metadata": metadata,
                    }
            except Exception as e:
                logger.warning(f"Error leyendo {json_path}: {e}")

    def get_catalog(self) -> List[Dict]:
        """Retorna lista de plugins disponibles"""
        plugins = self.catalog.get("plugins", [])
        
        # Agregar info de instalación
        for plugin in plugins:
            plugin_id = plugin.get("id")
            if plugin_id in self.installed_plugins:
                plugin["installed"] = True
                plugin["installed_version"] = (
                    self.installed_plugins[plugin_id]["metadata"].get("version")
                )
            else:
                plugin["installed"] = False

        return plugins

    def search_plugins(self, query: str) -> List[Dict]:
        """Busca plugins por nombre o descripción"""
        query = query.lower()
        results = []

        for plugin in self.get_catalog():
            name = plugin.get("name", "").lower()
            desc = plugin.get("description", "").lower()
            tags = [t.lower() for t in plugin.get("tags", [])]

            if query in name or query in desc or query in tags:
                results.append(plugin)

        return results

    def get_plugin_details(self, plugin_id: str) -> Optional[Dict]:
        """Obtiene detalles de un plugin específico"""
        for plugin in self.catalog.get("plugins", []):
            if plugin.get("id") == plugin_id:
                return plugin
        return None

    def install_plugin(
        self,
        plugin_id: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[bool, str]:
        """
        Instala un plugin desde GitHub

        Args:
            plugin_id: ID del plugin
            progress_callback: Función para reportar progreso

        Returns:
            (éxito, mensaje)
        """
        plugin = self.get_plugin_details(plugin_id)
        if not plugin:
            return False, "Plugin no encontrado en catálogo"

        # Obtener URL de descarga
        download_url = plugin.get("download_url")
        if not download_url:
            return False, "URL de descarga no especificada"

        try:
            if progress_callback:
                progress_callback("Descargando plugin...")

            # Descargar
            response = requests.get(download_url, timeout=30)
            if response.status_code != 200:
                return False, f"Error descargando: HTTP {response.status_code}"

            # Extraer
            if progress_callback:
                progress_callback("Extrayendo archivos...")

            plugin_folder = os.path.join(self.plugins_dir, plugin_id)
            
            # Limpiar si ya existe
            if os.path.exists(plugin_folder):
                shutil.rmtree(plugin_folder)

            os.makedirs(plugin_folder, exist_ok=True)

            # Extraer ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_ref:
                # El ZIP típicamente tiene estructura: plugin-name-main/
                members = zip_ref.namelist()
                
                # Encontrar carpeta raíz
                root_dirs = set()
                for member in members:
                    parts = member.split("/")
                    if len(parts) > 1:
                        root_dirs.add(parts[0])

                # Extraer en la raíz del plugin_folder
                if len(root_dirs) == 1:
                    # Estructura típica de GitHub: carpeta-raíz/contenido
                    root = list(root_dirs)[0]
                    for member in members:
                        if member.startswith(root + "/"):
                            relative = member[len(root) + 1 :]
                            if relative:
                                path = os.path.join(plugin_folder, relative)
                                if member.endswith("/"):
                                    os.makedirs(path, exist_ok=True)
                                else:
                                    os.makedirs(os.path.dirname(path), exist_ok=True)
                                    with zip_ref.open(member) as source, open(
                                        path, "wb"
                                    ) as target:
                                        target.write(source.read())
                else:
                    # Extraer directamente
                    zip_ref.extractall(plugin_folder)

            # Validar estructura
            if not os.path.exists(os.path.join(plugin_folder, "plugin.json")):
                shutil.rmtree(plugin_folder)
                return False, "Plugin no contiene plugin.json válido"

            if progress_callback:
                progress_callback("Instalado ✓")

            self._scan_installed()
            return True, "Plugin instalado correctamente"

        except Exception as e:
            logger.error(f"Error instalando {plugin_id}: {e}", exc_info=True)
            # Limpiar en caso de error
            plugin_folder = os.path.join(self.plugins_dir, plugin_id)
            if os.path.exists(plugin_folder):
                shutil.rmtree(plugin_folder)
            return False, f"Error: {str(e)}"

    def uninstall_plugin(self, plugin_id: str) -> tuple[bool, str]:
        """Desinstala un plugin"""
        if plugin_id not in self.installed_plugins:
            return False, "Plugin no instalado"

        try:
            plugin_path = self.installed_plugins[plugin_id]["path"]
            shutil.rmtree(plugin_path)
            self._scan_installed()
            return True, "Plugin desinstalado correctamente"
        except Exception as e:
            logger.error(f"Error desinstalando {plugin_id}: {e}", exc_info=True)
            return False, f"Error: {str(e)}"

    def is_installed(self, plugin_id: str) -> bool:
        """Verifica si un plugin está instalado"""
        return plugin_id in self.installed_plugins

    def refresh_catalog(self) -> bool:
        """Actualiza el catálogo desde GitHub"""
        try:
            response = requests.get(self.CATALOG_URL, timeout=5)
            if response.status_code == 200:
                self.catalog = response.json()
                cache_file = os.path.join(self.cache_dir, "catalog.json")
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(self.catalog, f, indent=2)
                return True
        except Exception as e:
            logger.warning(f"Error actualizando catálogo: {e}")
        return False
