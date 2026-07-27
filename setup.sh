#!/bin/bash

# 1. Dynamically resolve the absolute installation path (prevents 'pwd' breaking if run from elsewhere)
DIR_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="MintpaperEngine"
DESKTOP_FILE="$HOME/.local/share/applications/mintpaper.desktop"
AUTOSTART_FILE="$HOME/.config/autostart/mintpaper.desktop"

echo "Step 1: Cleaning up old environment and logs..."
rm -f "$DESKTOP_FILE"
rm -f "$AUTOSTART_FILE"
rm -f "$DIR_PATH/startup_error.log"

echo "Step 2: Installing system dependencies..."
# Added wmctrl and x11-utils because the Coma Tracker requires them for AABB occlusion math
sudo apt update && sudo apt install -y \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.1 \
    gir1.2-ayatanaappindicator3-0.1 \
    mpv \
    libmpv-dev \
    python3-venv \
    wmctrl \
    x11-utils

echo "Step 3: Setting up Virtual Environment (with System Bridge)..."
cd "$DIR_PATH" || exit
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install psutil pynput python-mpv

echo "Step 4: Creating the robust launch wrapper..."
# Replaced the old generation block with our dynamic, terminal-friendly launch script
# Note the quotes around 'EOF', which stops bash from evaluating variables during creation
cat << 'EOF' > "$DIR_PATH/launch.sh"
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
EOF

chmod +x "$DIR_PATH/launch.sh"
chmod +x "$DIR_PATH/main.py"

echo "Step 5: Generating the Start Menu & Autostart shortcuts..."
ICON_PATH="$DIR_PATH/presets/circle/icon.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_VALUE="preferences-desktop-wallpaper"
else
    ICON_VALUE="$ICON_PATH"
fi

DESKTOP_ENTRY="[Desktop Entry]
Type=Application
Name=Mintpaper Engine
Comment=Interactive HTML Wallpapers
Exec=$DIR_PATH/launch.sh
Path=$DIR_PATH
Icon=$ICON_VALUE
Terminal=false
Categories=Utility;Settings;
X-GNOME-Autostart-enabled=true"

# Write to Applications Menu
mkdir -p "$HOME/.local/share/applications"
echo "$DESKTOP_ENTRY" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# Write to Autostart (Can be manually removed if you only want terminal access for now)
mkdir -p "$HOME/.config/autostart"
echo "$DESKTOP_ENTRY" > "$AUTOSTART_FILE"

update-desktop-database ~/.local/share/applications/

echo "------------------------------------------------"
echo "INSTALLATION COMPLETE"
echo "Directory: $DIR_PATH"
echo "The engine is now configured for your Linux Mint environment."
echo "------------------------------------------------"