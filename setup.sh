#!/bin/bash

# 1. Define Paths (No spaces, absolute paths)
APP_NAME="MintpaperEngine"
DIR_PATH="$(pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/mintpaper.desktop"

echo "Step 1: Cleaning up old environment and logs..."
rm -f "$DESKTOP_FILE"
rm -f "$DIR_PATH/startup_error.log"

echo "Step 2: Installing system dependencies..."
sudo apt update && sudo apt install -y python3-gi gir1.2-gtk-3.0 gir1.2-webkit2-4.1 mpv libmpv-dev python3-venv

echo "Step 3: Setting up Virtual Environment (with System Bridge)..."
# We recreate the venv to ensure it maps to the new path correctly
rm -rf venv
python3 -m venv --system-site-packages venv
source venv/bin/activate
pip install psutil pynput python-mpv

echo "Step 4: Creating the launch wrapper..."
cat <<EOF > "$DIR_PATH/launch.sh"
#!/bin/bash
export DISPLAY=:0
cd "$DIR_PATH"
"./venv/bin/python3" "main.py" > "$DIR_PATH/startup_error.log" 2>&1
EOF

chmod +x "$DIR_PATH/launch.sh"
chmod +x "$DIR_PATH/main.py"

echo "Step 5: Generating the Start Menu shortcut..."
ICON_PATH="$DIR_PATH/presets/circle/icon.png"
if [ ! -f "$ICON_PATH" ]; then
    ICON_VALUE="preferences-desktop-wallpaper"
else
    ICON_VALUE="$ICON_PATH"
fi

echo "[Desktop Entry]
Type=Application
Name=Mintpaper Engine
Comment=Interactive HTML Wallpapers
Exec=$DIR_PATH/launch.sh
Path=$DIR_PATH
Icon=$ICON_VALUE
Terminal=false
Categories=Utility;Settings;" > "$DESKTOP_FILE"

chmod +x "$DESKTOP_FILE"
update-desktop-database ~/.local/share/applications/

echo "------------------------------------------------"
echo "INSTALLATION COMPLETE"
echo "Directory: $DIR_PATH"
echo "You can now launch 'Mintpaper Engine' from your menu."
echo "------------------------------------------------"