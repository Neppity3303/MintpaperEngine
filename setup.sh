#!/bin/bash

# 1. Define Paths
APP_NAME="MintpaperEngine"
DIR_PATH="$(pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/mintpaper.desktop"
AUTOSTART_FILE="$HOME/.config/autostart/mintpaper.desktop"

echo "Step 1: Cleaning up old environment and logs..."
rm -f "$DESKTOP_FILE"
rm -f "$AUTOSTART_FILE"
rm -f "$DIR_PATH/startup_error.log"

echo "Step 2: Installing system dependencies..."
# Added gir1.2-ayatanaappindicator3-0.1 for the system tray
sudo apt update && sudo apt install -y \
    python3-gi \
    gir1.2-gtk-3.0 \
    gir1.2-webkit2-4.1 \
    gir1.2-ayatanaappindicator3-0.1 \
    mpv \
    libmpv-dev \
    python3-venv

echo "Step 3: Setting up Virtual Environment (with System Bridge)..."
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install psutil pynput python-mpv

echo "Step 4: Creating the launch wrapper..."
# We added XDG_CURRENT_DESKTOP to ensure the tray icon renders correctly on Mint
cat <<EOF > "$DIR_PATH/launch.sh"
#!/bin/bash
export DISPLAY=:0
export XDG_CURRENT_DESKTOP=Cinnamon
cd "$DIR_PATH"
"./venv/bin/python3" "main.py" >> "$DIR_PATH/startup_error.log" 2>&1
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
echo "$DESKTOP_ENTRY" > "$DESKTOP_FILE"
chmod +x "$DESKTOP_FILE"

# Write to Autostart
mkdir -p "$HOME/.config/autostart"
echo "$DESKTOP_ENTRY" > "$AUTOSTART_FILE"

update-desktop-database ~/.local/share/applications/

echo "------------------------------------------------"
echo "INSTALLATION COMPLETE"
echo "Directory: $DIR_PATH"
echo "The engine will now start automatically at login."
echo "You can also launch it from your Start Menu."
echo "------------------------------------------------"