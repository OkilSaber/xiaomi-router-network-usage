#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Build Xiaomi Wi-Fi Dashboard (Linux) ==="

VENV_DIR="$DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel local dans $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"

# 1. Vérification stricte de pip (PAS d'installation de pip)
if ! "$PYTHON" -m pip --version >/dev/null 2>&1; then
    echo "❌ Erreur : 'pip' n'est pas disponible dans l'environnement Python ($PYTHON)."
    echo "   Veuillez installer pip ou utiliser un interpréteur Python incluant pip."
    exit 1
fi

# 2. Vérification des dépendances et de PyInstaller (installation uniquement si nécessaire)
if ! "$PYTHON" -c "import PyInstaller, flask, requests, urllib3, mac_vendor_lookup, webview" >/dev/null 2>&1; then
    echo "📦 Installation des dépendances nécessaires et de PyInstaller..."
    "$PYTHON" -m pip install -r "$DIR/requirements.txt" pyinstaller
fi

# Exécution du script de build
"$PYTHON" "$DIR/build.py"

echo "=== Build terminé avec succès dans $DIR/dist ==="
