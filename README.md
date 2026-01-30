**Mintpaper Engine**

A lightweight, interactive wallpaper engine for Linux Mint. Mintpaper Engine allows you to run HTML/JS/CSS presets or videos as your desktop wallpaper with support for multi-monitor setups, system-tray control, and real-time system stat injection.
Installation and Requirements
Linux Mint 22.3

**If you want to collaborate please contact me on discord @nepputty**

The included setup.sh script is optimized for Linux Mint 22.3. Running the script will automatically detect and install all necessary system headers and Python dependencies.
Linux Mint 22.2 and Older

If you are running version 22.2, the automatic installer may not be able to resolve all system-level dependencies. You must manually ensure the following packages are installed via apt before running the setup script:
Bash

sudo apt update
sudo apt install libayatana-appindicator3-dev gobject-introspection gir1.2-webkit2-4.1 libgirepository1.0-dev

**General Setup**

Once the system prerequisites are met, clone the repository and run the automated setup:
Bash

git clone https://github.com/Neppity3303/MintpaperEngine.git
cd MintpaperEngine
bash setup.sh

**Creating Interactive Presets**

The engine looks for an index.html file within your folder in the /presets/ directory.
Input Handling

The engine injects mouse and click data directly into the JavaScript context. Implement these functions in your window object to make your wallpaper responsive:
JavaScript

// Monitor-space mouse coordinates
window.updateMouse = (x, y) => {
    // Logic for eye-tracking or hover effects
};

// Mouse button state
window.updateClick = (isPressed) => {
    // Logic for click-to-animate or interaction
};

**Hardware Integration**

Real-time system statistics are pushed to the wallpaper every 2 seconds. This allows for reactive elements based on PC performance.
JavaScript

window.updateStats = (stats) => {
    // Available data:
    // stats.cpu (Percentage)
    // stats.ram (Percentage)
    // stats.disk (Percentage)
};

**Performance Tuning**

Users can set a frame rate limit via the Control Panel. To respect this limit in your code, use the following hook:
JavaScript

window.setFPS = (limit) => {
    // Logic to update your animation timing or requestAnimationFrame loop
};

**Key Features**

    Instance Locking: Uses Linux Abstract Sockets (\0) to prevent multiple engine instances from running simultaneously.

    Non-Persistent UI: The Control Panel is designed to be hidden, not destroyed, allowing it to maintain state and reappear instantly from the tray.

    Auto-Pathing: The setup.sh script generates absolute paths for the launcher, ensuring the engine can be moved between directories without breaking the Mint Menu shortcut.

**Project Structure**

    engine/: Core logic for window management, audio, and display syncing.

    ui/: Gtk code for the Control Panel and system tray indicator.

    presets/: Directory for HTML and Video wallpaper assets.

    launch.sh: The primary entry point that activates the virtual environment and starts the engine.

**Bugs**

The icon issue should be resolved. If errors continue notify me.

Mintpaper Engine mutes spotify and possibly some other applications. You can fix this by opening the sound app, going to the applications tab and unmuting it

Performance mode doesn't work right now. It might take a while to get it up and running.
