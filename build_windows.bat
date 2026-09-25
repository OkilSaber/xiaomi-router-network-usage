@echo off
setlocal
echo === Build Xiaomi Wi-Fi Dashboard (Windows) ===

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    exit /b 1
)

python -c "import PyInstaller" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installation de PyInstaller...
    python -m pip install pyinstaller
)

python build.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Le build a echoue.
    exit /b %ERRORLEVEL%
)

echo === Build Windows termine avec succes dans le dossier dist ===
pause
