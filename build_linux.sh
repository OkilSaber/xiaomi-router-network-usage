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

echo "Installation/mise à jour des dépendances dans le venv..."
"$PYTHON" -m pip install -r "$DIR/requirements.txt" pyinstaller

# Exécution du script de build
"$PYTHON" "$DIR/build.py"

echo "=== Build terminé avec succès dans $DIR/dist ==="
