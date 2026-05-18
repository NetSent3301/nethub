@echo off
chcp 65001 >nul
echo.
echo ========================================
echo   NetHUB Ultimate - Pruebas
echo ========================================
echo.

python -m pytest tests\test_core.py -v --tb=short 2>nul
if %errorlevel% neq 0 (
    echo pytest no disponible, usando unittest...
    python -m unittest discover -s tests -p "test_*.py" -v
)

echo.
pause
