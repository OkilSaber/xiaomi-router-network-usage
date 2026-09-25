#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Build Xiaomi Wi-Fi Dashboard (macOS) ==="

VENV_DIR="$DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Création de l'environnement virtuel local dans $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"

echo "Installation/mise à jour des dépendances dans le venv..."
"$PYTHON" -m pip install -r "$DIR/requirements.txt" pyinstaller

"$PYTHON" "$DIR/build.py"

echo "=== Build macOS terminé avec succès (.app & .dmg dans $DIR/dist) ==="

