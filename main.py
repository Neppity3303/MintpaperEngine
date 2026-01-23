#!/usr/bin/env python3
import socket
import sys

_instance_lock_socket = None

def ensure_single_instance():
    lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        lock_socket.bind('\0mintpaper_engine_lock')
        return lock_socket
    except socket.error:
        print("Wallpapery: Mintpaper is already running in the background.")
        sys.exit(0)

ensure_single_instance()


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1') 
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib, Gdk # Added Gdk for signals
from gi.repository import AyatanaAppIndicator3 as AppIndicator
import os
import json
import sys
import psutil
from pynput import mouse

# --- PORTABILITY FIX ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.environ['PYTHONUNBUFFERED'] = '1'

try:
    from engine.window import MintpaperEngine
    from engine.audio import AudioController
    from ui.editor import MintpaperControlPanel
    from engine.display import sync_config, get_monitor_data
except ImportError as e:
    print(f"Error: Could not find engine components. {e}")
    sys.exit(1)

class WallpaperyApp:
    def __init__(self):
        print("Wallpapery: Starting MintpaperEngine manager...")
        
        # 1. Hardware Discovery & Configuration Sync
        # This replaces manual load_config and the temp_scanner
        self.config = sync_config(os.path.join(BASE_DIR, "config.json"))
        self.engines = []

        # 2. Setup Windows for each monitor detected in config.json
        for mon_data in self.config["monitors"]:
            self.setup_monitor(mon_data)

        # 3. Audio & UI Setup
        self.audio_ctrl = AudioController(engines=self.engines)
        self.audio_ctrl.start()
        self.ui = MintpaperControlPanel(self)

        # 4. Global Interactivity (Mouse Listener)
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move, on_click=self.on_mouse_click)
        self.mouse_listener.start()

        # 5. --- SYSTEM EVENT LISTENER ---
        # If you rotate a monitor or plug a new one in, this triggers a reload
        self.screen = Gdk.Screen.get_default()
        if self.screen:
            self.screen.connect("monitors-changed", self.on_monitors_changed)

        GLib.timeout_add(500, self.update_loop)
        GLib.timeout_add(2000, self.update_system_stats)

    def setup_tray(self):
        self.indicator = AppIndicator.Indicator.new(
            "mintpaper-engine",
            "desktop",
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        menu = Gtk.Menu()
        item_panel = Gtk.MenuItem(label="Control Panel")
        item_panel.connect("activate", lambda _: self.editor.present())
        menu.append(item_panel)

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", self.on_quit)
        menu.append(item_quit)

        menu.show_all()
        self.indicator.set_menu(menu)

    def on_quit(self, *args):
        print("Mintpaper: Cleaning up engine...")
        for engine in self.engines:
            engine.window.destroy()
            
        if hasattr(self, 'editor') and self.editor:
            self.editor.destroy()
        Gtk.main_quit()

    def on_monitors_changed(self, screen):
        """Triggers when Linux Mint detects a display geometry change."""
        print("Wallpapery: Display geometry changed! Syncing config and reloading...")
        self.config = sync_config(os.path.join(BASE_DIR, "config.json"))
        self.reload_engines()

    def on_mouse_move(self, x, y):
        for engine in self.engines:
            # Multi-monitor coordinate check
            # engine.mon['geometry'] contains the 'x', 'y', 'w', 'h' from display.py
            geo = engine.mon['geometry']
            local_x = x - geo['x']
            local_y = y - geo['y']
            
            if 0 <= local_x <= geo['w'] and 0 <= local_y <= geo['h']:
                script = f"if(window.updateMouse) {{ window.updateMouse({local_x}, {local_y}); }}"
                GLib.idle_add(engine.webview.run_javascript, script, None, None, None)

    def on_mouse_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            val = "true" if pressed else "false"
            for engine in self.engines:
                if hasattr(engine, 'webview') and engine.webview:
                    script = f"if(window.updateClick) {{ window.updateClick({val}); }}"
                    GLib.idle_add(engine.webview.run_javascript, script, None, None, None)

    def update_system_stats(self):
        stats = {
            "cpu": psutil.cpu_percent(interval=None),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent
        }
        json_stats = json.dumps(stats)
        for engine in self.engines:
            if hasattr(engine, 'webview') and engine.webview is not None:
                script = f"if (window.updateStats) {{ updateStats({json_stats}); }}"
                # We use idle_add to ensure thread-safe UI updates
                GLib.idle_add(engine.webview.run_javascript, script, None, None, None)
        return True 
    
    def save_config(self):
        config_path = os.path.join(BASE_DIR, "config.json")
        try:
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            print("Wallpaper: Config saved.")
        except Exception as e:
            print(f"Wallpaper: Error saving config: {e}")

    def setup_monitor(self, mon_data):
        engine = MintpaperEngine(mon_data)
        self.engines.append(engine)
        
        # Pull the preset path from the monitor config, fallback to default
        path = mon_data.get("active_preset_path") or os.path.join(BASE_DIR, "presets", "circle", "circle.html")

        if path and os.path.exists(path):
            if path.lower().endswith('.html'):
                print(f"Wallpapery: Loading Monitor {mon_data['id']} ({mon_data['name']}): {path}")
                engine.load_html(path)
            else:
                engine.load_video(path)
            
            fps_limit = mon_data.get("fps_limit", 60)
            GLib.timeout_add(1000, lambda: engine.webview.run_javascript(f"if(window.setFPS) {{ setFPS({fps_limit}); }}"))

        # Standard wallpaper "keep-below" forcing
        GLib.timeout_add(200, self.force_lower_engine, engine)
        GLib.timeout_add(1000, self.force_lower_engine, engine)

    def force_lower_engine(self, engine):
        if hasattr(engine, 'window') and engine.window.get_window():
            engine.window.set_keep_below(True)
            engine.window.get_window().lower()
        return False

    def reload_engines(self):
        print("Wallpapery: Hot-reloading engines...")
        for engine in self.engines:
            engine.window.destroy()
        self.engines = []
        
        # Re-run the setup loop with updated config
        for mon_data in self.config["monitors"]:
            self.setup_monitor(mon_data)
        
        self.audio_ctrl.engines = self.engines
        self.audio_ctrl.start()

    def update_loop(self):
        try:
            for engine in self.engines:
                vol = engine.mon.get("volume", 50) / 100.0
                if engine.mon.get("is_muted"):
                    vol = 0

                script = f"if(window.updateVolume) {{ updateVolume({vol}); }}"
                engine.webview.run_javascript(script)

            self.audio_ctrl.update()
        except Exception as e:
            print(f"Wallpapery: Audio update error: {e}")
        return True

if __name__ == "__main__":
    _instance_lock = ensure_single_instance()
    app = WallpaperyApp()
    print("Wallpapery: Active. Press Ctrl+C to exit.")
    Gtk.main()