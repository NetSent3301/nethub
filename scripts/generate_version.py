#!/usr/bin/env python3
"""
Script para generar version.json basado en git tags o versión manual.
"""
import json
import os
import subprocess
import sys
from datetime import datetime


def get_git_version():
    """Obtener versión desde git tags."""
    try:
        # Obtener el tag más reciente
        tag = subprocess.check_output(
            ['git', 'describe', '--tags', '--abbrev=0'], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        # Remover el prefijo 'v' si existe
        if tag.startswith('v'):
            tag = tag[1:]
            
        return tag
    except subprocess.CalledProcessError:
        return None


def get_current_version():
    """Obtener versión actual del proyecto."""
    # Primero intentar desde git tag
    git_version = get_git_version()
    if git_version:
        return git_version
    
    # Si no hay tags, usar versión por defecto o leer de archivo existente
    version_file = 'version.json'
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                data = json.load(f)
                return data.get('version', '1.0.0')
        except:
            pass
    
    return '1.0.0'


def get_github_repo():
    """Obtener owner/repo desde git remote origin."""
    try:
        remote = subprocess.check_output(
            ['git', 'config', '--get', 'remote.origin.url'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if remote.startswith('git@'):
            remote = remote.replace('git@', 'https://').replace(':', '/')
        if remote.endswith('.git'):
            remote = remote[:-4]
        parts = remote.rstrip('/').split('/')
        return f"{parts[-2]}/{parts[-1]}"
    except Exception:
        return "NetSent3301/nethub-distro"


def generate_version_json():
    """Generar el archivo version.json."""
    version = get_current_version()
    repo = get_github_repo()
    
    # Estructura básica del version.json
    version_data = {
        "version": version,
        "release_date": datetime.now().strftime("%Y-%m-%d"),
        "min_version": ".".join(str(int(x)) for x in version.split('.')[:-1] + ['0']),  # Ej: 2.0.0 para 2.0.1
        "download_url": f"https://github.com/{repo}/releases/download/v{version}/NetHUB_Ultimate_{version}.zip",
        "changelog": get_changelog(),
        "mandatory": False,
        "message": f"Actualización a la versión {version}"
    }
    
    # Escribir el archivo
    with open('version.json', 'w', encoding='utf-8') as f:
        json.dump(version_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ version.json generado con versión {version}")
    return version_data


def get_changelog():
    """Obtener changelog desde git commits desde el último tag."""
    try:
        # Obtener commits desde el último tag
        last_tag = subprocess.check_output(
            ['git', 'describe', '--tags', '--abbrev=0'], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        # Obtener commits desde ese tag
        commits = subprocess.check_output(
            ['git', 'log', f'{last_tag}..HEAD', '--pretty=format:- %s'], 
            stderr=subprocess.DEVNULL
        ).decode().strip()
        
        if commits:
            return commits.split('\n')
        else:
            return ["Actualización general"]
            
    except subprocess.CalledProcessError:
        # Si no hay tags previos, obtener todos los commits
        try:
            commits = subprocess.check_output(
                ['git', 'log', '--pretty=format:- %s', '-n', '10'],  # Últimos 10 commits
                stderr=subprocess.DEVNULL
            ).decode().strip()
            return commits.split('\n') if commits else ["Actualización inicial"]
        except:
            return ["Actualización"]


if __name__ == "__main__":
    # Asegurarnos de estar en el directorio correcto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    os.chdir(project_dir)
    
    generate_version_json()