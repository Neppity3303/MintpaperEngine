import gi
import json
import os

# We specify version 3.0 for Linux Mint (Cinnamon/X11) compatibility
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk

def get_monitor_data():
    """
    Scans the system for all connected monitors and returns a list 
    of dictionaries containing geometry and hardware info.
    """
    display = Gdk.Display.get_default()
    if not display:
        return []

    monitors = []
    
    # Iterate through all detected outputs
    for i in range(display.get_n_monitors()):
        monitor = display.get_monitor(i)
        geometry = monitor.get_geometry()
        
        # Pull manufacturer and model (handles potential NULL/None values)
        brand = monitor.get_manufacturer() or "Generic"
        model = monitor.get_model() or f"Display-{i}"
        
        # Calculate orientation based on relative width/height
        orientation = "portrait" if geometry.height > geometry.width else "landscape"

        monitors.append({
            "id": i,
            "name": f"{brand} {model}",
            "isPrimary": monitor.is_primary(),
            "geometry": {
                "x": geometry.x,
                "y": geometry.y,
                "w": geometry.width,
                "h": geometry.height
            },
            "orientation": orientation,
            "scale_factor": monitor.get_scale_factor(),
            "is_muted": False,
            "volume": 50,
            "performance mode": True,
            "fps_limit": 60,
            "active preset_path": os.path.join("presets", "circle", "circle.html")
        })
    
    return monitors

def sync_config(config_path="config.json"):
    """
    Updates the config.json file by comparing current hardware 
    against saved settings.
    """
    current_hardware = get_monitor_data()
    
    # Ensure the config file exists
    if not os.path.exists(config_path):
        default_config = {
            "engine_version": "1.0.0",
            "monitors": current_hardware
        }
        with open(config_path, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

    # Load existing config
    with open(config_path, 'r') as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError:
            config = {"engine_version": "1.0.0", "monitors": []}

    # MERGE LOGIC: Update existing monitor geometries but keep user settings
    # For a public engine, we match by Monitor ID or Name
    updated_monitors = []
    for hardware in current_hardware:
        # Check if we already have settings for this monitor
        existing = next((m for m in config["monitors"] if m["name"] == hardware["name"]), None)
        
        if existing:
            # Update physical data (geometry changes)
            existing["geometry"] = hardware["geometry"]
            existing["isPrimary"] = hardware["isPrimary"]
            existing["orientation"] = hardware["orientation"]
            updated_monitors.append(existing)
        else:
            # New monitor found!
            hardware["active_preset"] = "default"
            updated_monitors.append(hardware)

    config["monitors"] = updated_monitors
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
        
    return config