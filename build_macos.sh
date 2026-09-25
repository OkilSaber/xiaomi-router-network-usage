#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=== Build Xiaomi Wi-Fi Dashboard (macOS) ==="

PYTHON="python3"
if [ -x "$DIR/bin/python" ]; then
    PYTHON="$DIR/bin/python"
elif [ -x "$DIR/.venv/bin/python" ]; then
    PYTHON="$DIR/.venv/bin/python"
fi

if ! "$PYTHON" -c "import PyInstaller" 2>/dev/null; then
    echo "Installation de PyInstaller..."
    "$PYTHON" -m pip install pyinstaller
fi

"$PYTHON" "$DIR/build.py"

echo "=== Build macOS terminé avec succès dans $DIR/dist ==="
