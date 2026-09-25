#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Build Xiaomi Wi-Fi Dashboard (Linux) ==="

# Sélectionner l'interpréteur Python
if [ -x "$DIR/bin/python" ]; then
    PYTHON="$DIR/bin/python"
elif [ -x "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
else
    PYTHON="python"
fi

# Vérification ou installation de PyInstaller
if ! "$PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "Installation de PyInstaller..."
    "$PYTHON" -m pip install pyinstaller
fi

# Exécution du script de build
"$PYTHON" "$DIR/build.py"

echo "=== Build terminé avec succès dans $DIR/dist ==="
