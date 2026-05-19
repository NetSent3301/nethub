#!/usr/bin/env python3
"""
Script para crear un release en GitHub usando solo git y la API de GitHub.
Requiere un token de acceso personal de GitHub con permisos de repo.
"""
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path


def run_cmd(cmd, capture=True):
    """Ejecutar comando y retornar resultado."""
    try:
        if capture:
            result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
            return result.decode().strip()
        else:
            subprocess.check_call(cmd, shell=True)
            return ""
    except subprocess.CalledProcessError as e:
        if capture:
            return e.output.decode().strip() if e.output else str(e)
        raise


def get_git_info():
    """Obtener información del repositorio git."""
    # Obtener URL del remoto origin
    remote_url = run_cmd('git config --get remote.origin.url')
    
    # Convertir a formato HTTPS si es SSH
    if remote_url.startswith('git@'):
        remote_url = remote_url.replace('git@', 'https://').replace(':', '/')
    if remote_url.endswith('.git'):
        remote_url = remote_url[:-4]
    
    # Extraer owner y repo
    parts = remote_url.rstrip('/').split('/')
    owner = parts[-2]
    repo = parts[-1]
    
    return owner, repo, remote_url


def get_latest_tag():
    """Obtener el tag más reciente o crear uno nuevo basado en version.json."""
    version_file = Path('version.json')
    if version_file.exists():
        with open(version_file, 'r') as f:
            data = json.load(f)
            version = data.get('version', '1.0.0')
            tag = f"v{version}"
            
            # Verificar si el tag ya existe
            try:
                run_cmd(f'git show-ref --tags --verify --quiet refs/tags/{tag}')
                return tag  # Tag existe
            except:
                return tag  # Tag no existe, lo usaremos para crear release
    
    return "v1.0.0"


def create_github_release(tag_name, release_name, body, draft=False, prerelease=False):
    """Crear un release en GitHub usando la API."""
    # Obtener token de variable de entorno
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ Error: GITHUB_TOKEN no está configurado en variables de entorno")
        print("   Configura tu token de acceso personal: $env:GITHUB_TOKEN='tu_token_aqui'")
        return False
    
    owner, repo, _ = get_git_info()
    
    # Preparar datos para la API
    release_data = {
        "tag_name": tag_name,
        "target_commitish": "main",  # o 'master' según tu rama principal
        "name": release_name,
        "body": body,
        "draft": draft,
        "prerelease": prerelease
    }
    
    # URL de la API
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    
    # Preparar request
    data = json.dumps(release_data).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': f'token {token}',
            'Content-Type': 'application/json',
            'User-Agent': 'NetHUB-Release-Script'
        }
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"✅ Release creado exitosamente: {result['html_url']}")
            return result
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode() if e.read() else str(e)
        print(f"❌ Error HTTP {e.code}: {error_msg}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False


def upload_asset(release_id, file_path, label=None):
    """Subir un asset al release."""
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("❌ Error: GITHUB_TOKEN no está configurado")
        return False
    
    owner, repo, _ = get_git_info()
    
    # Determinar content type basado en extensión
    import mimetypes
    content_type, _ = mimetypes.guess_type(file_path)
    if content_type is None:
        content_type = 'application/octet-stream'
    
    url = f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets"
    params = {"name": os.path.basename(file_path)}
    if label:
        params["label"] = label
    
    # Construir URL con parámetros
    from urllib.parse import urlencode
    url = f"{url}?{urlencode(params)}"
    
    # Leer el archivo
    with open(file_path, 'rb') as f:
        data = f.read()
    
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            'Authorization': f'token {token}',
            'Content-Type': content_type,
            'User-Agent': 'NetHUB-Release-Script'
        }
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())
            print(f"✅ Asset subido: {result['browser_download_url']}")
            return result
    except urllib.error.HTTPError as e:
        error_msg = e.read().decode() if e.read() else str(e)
        print(f"❌ Error HTTP {e.code} al subir asset: {error_msg}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al subir asset: {e}")
        return False


def main():
    """Función principal para crear release."""
    print("🚀 Iniciando creación de release para NetHUB...")
    
    # Cambiar al directorio del proyecto
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    os.chdir(project_dir)
    
    # Generar/actualizar version.json primero
    print("\n📋 Generando version.json...")
    version_script = script_dir / "generate_version.py"
    if version_script.exists():
        subprocess.run([sys.executable, str(version_script)], check=True)
    
    # Obtener información de versión
    version_file = Path('version.json')
    if not version_file.exists():
        print("❌ Error: version.json no encontrado")
        return 1
    
    with open(version_file, 'r') as f:
        version_data = json.load(f)
    
    version = version_data.get('version', '1.0.0')
    tag_name = f"v{version}"
    release_name = f"NetHUB Ultimate {version}"
    
    # Crear body del release desde changelog
    changelog = version_data.get('changelog', [])
    if isinstance(changelog, list):
        changelog_text = '\n'.join([f"• {item}" for item in changelog])
    else:
        changelog_text = str(changelog)
    
    body = f"""## NetHUB Ultimate {version}

{changelog_text}

### Descarga
- [NetHUB_Ultimate_{version}.zip]({version_data.get('download_url', '#')})

### Notas
Esta versión incluye mejoras y correcciones de errores.
"""
    
    print(f"\n🏷️  Creando release {tag_name}...")
    
    # Intentar obtener release existente o crear uno nuevo
    owner, repo, _ = get_git_info()
    
    # Primero verificar si el tag ya tiene un release
    try:
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}"
            req = urllib.request.Request(
                url,
                headers={
                    'Authorization': f'token {token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'NetHUB-Release-Script'
                }
            )
            
            with urllib.request.urlopen(req) as response:
                existing_release = json.loads(response.read().decode())
                print(f"ℹ️  Release existente encontrado: {existing_release['html_url']}")
                release_id = existing_release['id']
                
                # Preguntar si quiere actualizarlo
                response = input("\n¿Actualizar este release existente? (y/N): ").strip().lower()
                if response != 'y':
                    print("❌ Operación cancelada")
                    return 1
                    
                # En lugar de actualizar, eliminaremos y crearemos uno nuevo (más simple)
                # Nota: GitHub API no permite actualizar release directamente fácilmente
                print("ℹ️  Para actualizar, elimine el release existente en GitHub y vuelva a ejecutar")
                return 1
                
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Release no existe, continuamos para crearlo
            pass
        else:
            print(f"⚠️  Error al verificar release existente: {e.code}")
    except Exception as e:
        print(f"⚠️  Error al verificar release existente: {e}")
    
    # Crear nuevo release
    print("\n📦 Creando nuevo release...")
    release_result = create_github_release(
        tag_name=tag_name,
        release_name=release_name,
        body=body
    )
    
    if not release_result:
        return 1
    
    release_id = release_result['id']
    
    # Ahora crear el zip para subir
    print("\n📦 Creando paquete de distribución...")
    dist_dir = Path("dist")
    dist_dir.mkdir(exist_ok=True)
    
    zip_name = f"NetHUB_Ultimate_{version}.zip"
    zip_path = dist_dir / zip_name
    
    # Aquí normalmente empaquetarías tu aplicación
    # Para este ejemplo, crearemos un zip con los archivos principales
    import zipfile
    import shutil
    
    # Lista de archivos/directorios a incluir
    include_patterns = [
        "src/**",
        "assets/**",
        "config/**",
        "docs/**",
        "LICENCIA.txt",
        "README.md",
        "requirements.txt",
        "version.json"
    ]
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for pattern in include_patterns:
            if '*' in pattern:
                # Usar glob para patrones
                from glob import glob
                for file in glob(pattern, recursive=True):
                    if os.path.isfile(file):
                        # Ruta relativa dentro del zip
                        arcname = os.path.join("NetHUB_Ultimate", file)
                        zipf.write(file, arcname)
            else:
                # Archivo o directorio específico
                if os.path.isfile(pattern):
                    arcname = os.path.join("NetHUB_Ultimate", pattern)
                    zipf.write(pattern, arcname)
                elif os.path.isdir(pattern):
                    for root, dirs, files in os.walk(pattern):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.join("NetHUB_Ultimate", 
                                                 os.path.relpath(file_path, os.path.dirname(pattern)))
                            zipf.write(file_path, arcname)
    
    print(f"✅ Paquete creado: {zip_path}")
    
    # Subir el zip como asset
    print("\n📤 Subiendo paquete al release...")
    upload_asset(release_id, str(zip_path), f"NetHUB Ultimate {version}")
    
    print("\n🎉 Proceso completado!")
    print(f"   Release: {release_result['html_url']}")
    print(f"   Versión: {version}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())