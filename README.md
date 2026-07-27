**Mintpaper Engine**

A lightweight, interactive wallpaper engine for Linux Mint. Mintpaper Engine allows you to run HTML/JS/CSS presets or videos as your desktop wallpaper with support for multi-monitor setups, system-tray control, and real-time system stat injection.
Installation and Requirements
Linux Mint 22.3

**If you want to collaborate please contact me on discord @nepputty**

The included setup.sh script is optimized for Linux Mint 22.3. Running the script will automatically detect and install all necessary system headers and Python dependencies.
Linux Mint 22.2 and Older

If you are running version 22.2, the automatic installer may not be able to resolve all system-level dependencies. You must manually ensure the following packages are installed via apt before running the setup script:

**General Setup**

Clone the repository and run the automated setup:


git clone https://github.com/Neppity3303/MintpaperEngine/tree/main

cd MintpaperEngine

./setup.sh

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


