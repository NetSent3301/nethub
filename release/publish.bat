@echo off
chcp 65001 >nul

echo.
echo ========================================
echo   NetHUB Ultimate - Publicar Release
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set SRC_REPO=%SCRIPT_DIR%..\nethub-ultimate
set DIST_REPO=%SCRIPT_DIR%..\nethub-distro

echo Verificando Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Git no esta instalado o no esta en PATH
    pause
    exit /b 1
)

echo.
echo Subiendo repo de codigo fuente...
cd /d "%SRC_REPO%"
if errorlevel 1 (
    echo ERROR: No se encontro %SRC_REPO%
    pause
    exit /b 1
)

git add .
git commit -m "auto release" >nul 2>&1

git push -u origin master
if errorlevel 1 (
    echo ERROR: push fallo en nethub-ultimate
    pause
    exit /b 1
)

echo   + nethub-ultimate: subido

echo.
echo Subiendo repo de distribucion...
cd /d "%DIST_REPO%"
if errorlevel 1 (
    echo ERROR: No se encontro %DIST_REPO%
    pause
    exit /b 1
)

git add .
git commit -m "auto release" >nul 2>&1

git push -u origin master
if errorlevel 1 (
    echo ERROR: push fallo en nethub-distro
    pause
    exit /b 1
)

echo   + nethub-distro: subido

echo.
echo ========================================
echo   Release publicada en GitHub!
echo ========================================
echo.
pause