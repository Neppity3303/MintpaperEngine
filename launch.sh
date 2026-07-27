#!/bin/bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR" || { echo "Mintpaper: Failed to resolve directory"; exit 1; }

if [ -z "$DISPLAY" ]; then
    export DISPLAY=:0
fi
export XDG_CURRENT_DESKTOP=Cinnamon

LOG_FILE="$DIR/startup_error.log"
echo "Mintpaper: Starting Engine (v0.20 Architecture)..."

# Write to log and terminal simultaneously for easy debugging
"$DIR/venv/bin/python3" "$DIR/main.py" 2>&1 | tee "$LOG_FILE"
