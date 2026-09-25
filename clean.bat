@echo off
setlocal
echo === Nettoyage Xiaomi Wi-Fi Dashboard ===

python clean.py %*
if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Le nettoyage a rencontre un probleme.
    exit /b %ERRORLEVEL%
)

echo === Nettoyage termine ===
