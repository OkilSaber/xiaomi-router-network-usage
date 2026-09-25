@echo off
setlocal
echo === Build Xiaomi Wi-Fi Dashboard (Windows) ===

python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Python n'est pas installe ou n'est pas dans le PATH.
    exit /b 1
)

:: 1. Vérification stricte de pip (PAS d'installation de pip)
python -m pip --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] pip n'est pas disponible dans l'environnement Python courant.
    echo Veuillez installer pip ou activer un environnement virtuel le contenant.
    exit /b 1
)

:: 2. Vérification des dépendances et de PyInstaller
python -c "import PyInstaller, flask, requests, urllib3, mac_vendor_lookup, webview" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installation des dependances nécessaires et de PyInstaller...
    python -m pip install -r requirements.txt pyinstaller
)

python build.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Le build a echoue.
    exit /b %ERRORLEVEL%
)

echo === Build Windows termine avec succes dans le dossier dist ===
pause
