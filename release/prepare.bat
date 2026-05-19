@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================
echo   NetHUB Ultimate - Lanzador de Releases
echo ============================================
echo.
echo Este script automatiza el flujo completo:
echo   1. Pide datos de la nueva version
echo   2. Genera version.json
echo   3. Compila el .exe
echo   4. Prepara repos de codigo y distribucion
echo   5. Hace git commit en ambos repos
echo.

REM === CONFIG (cambiar una sola vez) ===
set GITHUB_USER=NetSent3301
set GITHUB_REPO_SRC=nethub-ultimate
set GITHUB_REPO_DIST=nethub-distro
set BRANCH=main

set PROJECT_DIR=%~dp0..
set BUILD_DIR=%PROJECT_DIR%\build
set DIST_DIR=%PROJECT_DIR%\dist
set SRC_REPO=%PROJECT_DIR%\..\nethub-ultimate
set DIST_REPO=%PROJECT_DIR%\..\nethub-distro

REM === PASO 1: Datos de la version ===
echo =========================================
echo   PASO 1: Datos de la nueva version
echo =========================================
echo.

set /p VERSION="Numero de version (ej: 2.1.0): "
if "%VERSION%"=="" (
    echo ERROR: Debes ingresar un numero de version.
    pause
    exit /b 1
)

set /p MANDATORY="Obligatoria? (s/N): "
if /i "%MANDATORY%"=="s" (
    set MANDATORY_JSON=true
) else (
    set MANDATORY_JSON=false
)

echo.
echo Cambios en esta version (uno por linea, Enter vacio para terminar):
set CHANGELOG_COUNT=0

:ADD_CHANGE
set "ITEM="
set /p ITEM="  - "
if not defined ITEM goto DONE_CHANGELOG
if "%ITEM%"=="" goto DONE_CHANGELOG
set CHANGELOG_COUNT=!CHANGELOG_COUNT!+1
set "CHANGELOG_!CHANGELOG_COUNT!=%ITEM%"
goto ADD_CHANGE
:DONE_CHANGELOG

set /p MESSAGE="Mensaje corto [Nueva version %VERSION% disponible.]: "
if "!MESSAGE!"=="" set MESSAGE=Nueva version %VERSION% disponible.

REM === PASO 2: Generar version.json ===
echo.
echo =========================================
echo   PASO 2: Generando version.json...
echo =========================================

for /f "tokens=*" %%a in ('powershell -Command "Get-Date -Format yyyy-MM-dd"') do set TODAY=%%a

(
echo {
echo   "version": "%VERSION%",
echo   "release_date": "%TODAY%",
echo   "min_version": "2.0.0",
echo   "download_url": "https://github.com/%GITHUB_USER%/%GITHUB_REPO_DIST%/raw/main/NetHUB_Ultimate.exe",
echo   "changelog": [
) > "%PROJECT_DIR%\version.json"

for /l %%i in (1,1,%CHANGELOG_COUNT%) do (
    set "ITEM=!CHANGELOG_%%i!"
    if %%i lss %CHANGELOG_COUNT% (
        echo     "!ITEM!",
    ) else (
        echo     "!ITEM!"
    )
) >> "%PROJECT_DIR%\version.json"

(
echo   ],
echo   "mandatory": %MANDATORY_JSON%,
echo   "message": "%MESSAGE%"
echo }
) >> "%PROJECT_DIR%\version.json"

echo   version.json generado: %PROJECT_DIR%\version.json

REM === PASO 3: Limpiar y compilar ===
echo.
echo =========================================
echo   PASO 3: Compilando .exe...
echo =========================================

if exist "%PROJECT_DIR%\src\__pycache__" rmdir /s /q "%PROJECT_DIR%\src\__pycache__"
if exist "%PROJECT_DIR%\src\modules\__pycache__" rmdir /s /q "%PROJECT_DIR%\src\modules\__pycache__"
if exist "%PROJECT_DIR%\src\modules\custom\__pycache__" rmdir /s /q "%PROJECT_DIR%\src\modules\custom\__pycache__"
if exist "%PROJECT_DIR%\tests\__pycache__" rmdir /s /q "%PROJECT_DIR%\tests\__pycache__"
if exist "%PROJECT_DIR%\NETHUB" rmdir /s /q "%PROJECT_DIR%\NETHUB"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
del /q "%PROJECT_DIR%\*.spec" 2>nul

cd /d "%PROJECT_DIR%"
pyinstaller --onefile --windowed --name="NetHUB_Ultimate" --icon=NONE src\main.py

if not exist "%DIST_DIR%\NetHUB_Ultimate.exe" (
    echo.
    echo ERROR: La compilacion fallo.
    pause
    exit /b 1
)
echo   .exe compilado exitosamente.

REM === PASO 4: Preparar repos ===
echo.
echo =========================================
echo   PASO 4: Preparando repositorios...
echo =========================================

REM Repo de distribucion
if exist "%DIST_REPO%" rmdir /s /q "%DIST_REPO%"
mkdir "%DIST_REPO%"
copy "%DIST_DIR%\NetHUB_Ultimate.exe" "%DIST_REPO%\" >nul
copy "%PROJECT_DIR%\LICENCIA.txt" "%DIST_REPO%\" >nul
copy "%PROJECT_DIR%\version.json" "%DIST_REPO%\" >nul

(
echo # NetHUB Ultimate v%VERSION%
echo.
echo ![Platform](https://img.shields.io/badge/platform-Windows-blue^)
echo ![License](https://img.shields.io/badge/license-Commercial-red^)
echo.
echo Aplicacion todo-en-uno con terminal interactiva, sistema de modulos, OSINT, hacking, cripto, monitoreo de sistema, reproductor de musica, notas, y mucho mas.
echo.
echo ## Descargar
echo.
echo ^| Version ^| Archivo ^| Estado ^|
echo ^|---------^|---------^|--------^|
echo ^| %VERSION% ^| [NetHUB_Ultimate.exe](./NetHUB_Ultimate.exe^) ^| Actual ^|
echo.
echo ## Requisitos
echo.
echo - Windows 10 o superior
echo - Sin dependencias externas (todo incluido en el .exe^)
echo.
echo ## Instalacion
echo.
echo 1. Descarga `NetHUB_Ultimate.exe`
echo 2. Ejecutalo directamente (no requiere instalacion^)
echo 3. Crea tu cuenta al primer inicio
echo.
echo ## Licencia
echo.
echo Licencia comercial. Consulta `LICENCIA.txt` para los terminos completos.
echo.
echo ## Contacto
echo.
echo - [GitHub Issues](../../issues^)
) > "%DIST_REPO%\README.md"

(
echo # User data (nunca commitear^)
echo users.json
echo config.json
echo chat_history.json
echo notes/
echo *.key
echo *.pem
echo google_oauth_client.json
) > "%DIST_REPO%\.gitignore"

REM Repo de codigo fuente
if exist "%SRC_REPO%" rmdir /s /q "%SRC_REPO%"
mkdir "%SRC_REPO%"
robocopy "%PROJECT_DIR%" "%SRC_REPO%" /E /XF *.pyc *.tmp *.log users.json config.json chat_history.json google_oauth_client.json *.key *.pem NetHUB_Ultimate.spec "desktop.ini" Thumbs.db /XD __pycache__ dist_repo dist "build\NetHUB_Ultimate" /NFL /NDL /NJH /NJS /NC /NS /NP

echo   Repos preparados.

REM === PASO 5: Git commit ===
echo.
echo =========================================
echo   PASO 5: Creando commits...
echo =========================================

cd /d "%SRC_REPO%"
git init >nul 2>&1
git add . >nul 2>&1
git commit -m "NetHUB Ultimate v%VERSION%" >nul 2>&1
echo   + nethub-ultimate: commit listo

cd /d "%DIST_REPO%"
git init >nul 2>&1
git add . >nul 2>&1
git commit -m "Release v%VERSION%" >nul 2>&1
echo   + nethub-distro: commit listo

REM === RESUMEN ===
echo.
echo ============================================
echo   Release v%VERSION% preparada!
echo ============================================
echo.
echo   version.json: %PROJECT_DIR%\version.json
echo   .exe:         %DIST_DIR%\NetHUB_Ultimate.exe
echo   codigo:       %SRC_REPO%
echo   distro:       %DIST_REPO%
echo.
echo =========================================
echo   PARA PUBLICAR EN GITHUB:
echo =========================================
echo.
echo   Si es la PRIMERA vez, ejecuta:
echo.
echo     cd "%SRC_REPO%"
echo     git remote add origin https://github.com/%GITHUB_USER%/%GITHUB_REPO_SRC%.git
echo     git branch -M main
echo     git push -u origin main
echo.
echo     cd "%DIST_REPO%"
echo     git remote add origin https://github.com/%GITHUB_USER%/%GITHUB_REPO_DIST%.git
echo     git branch -M main
echo     git push -u origin main
echo.
echo   Si YA publicaste antes, ejecuta:
echo.
echo     cd "%SRC_REPO%"
echo     git push
echo.
echo     cd "%DIST_REPO%"
echo     git push
echo.
pause
