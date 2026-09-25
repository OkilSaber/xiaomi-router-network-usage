#!/usr/bin/env bash
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -x "$DIR/dist/xiaomi_dashboard" ]; then
    exec "$DIR/dist/xiaomi_dashboard" "$@"
elif [ -x "$DIR/xiaomi_dashboard" ]; then
    exec "$DIR/xiaomi_dashboard" "$@"
elif [ -x "$DIR/bin/python" ]; then
    exec "$DIR/bin/python" "$DIR/xiaomi_wifi_dashboard.py" "$@"
elif [ -x "$DIR/.venv/bin/python" ]; then
    exec "$DIR/.venv/bin/python" "$DIR/xiaomi_wifi_dashboard.py" "$@"
elif command -v python3 >/dev/null 2>&1; then
    exec python3 "$DIR/xiaomi_wifi_dashboard.py" "$@"
else
    exec python "$DIR/xiaomi_wifi_dashboard.py" "$@"
fi
