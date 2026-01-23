#!/usr/bin/env python3

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1') 
from gi.repository import Gtk, GLib
import os
import json
import sys
import psutil
from pynput import mouse # Global listener

# --- PORTABILITY FIX: Define the base directory of the script ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Ensure logs appear in the terminal immediately
os.environ['PYTHONUNBUFFERED'] = '1'

try:
    from engine.window import MintpaperEngine
    from engine.audio import AudioController
    from ui.editor import MintpaperControlPanel
except ImportError as e:
    print(f"Error: Could not find engine components. {e}")
    sys.exit(1)

class WallpaperyApp:
    def __init__(self):
        print("Wallpapery: Starting MintpaperEngine manager...")
        
        self.config = self.load_config()
        self.engines = []

        temp_scanner = AudioController(engines=[])
        self.monitors = temp_scanner.monitors 
        
        for mon_data in self.monitors:
            self.setup_monitor(mon_data)

        self.audio_ctrl = AudioController(engines=self.engines)
        self.audio_ctrl.start()

        self.ui = MintpaperControlPanel(self)

        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move, on_click=self.on_mouse_click)
        self.mouse_listener.start()

        GLib.timeout_add(500, self.update_loop)
        GLib.timeout_add(2000, self.update_system_stats)

    def on_mouse_move(self, x, y):
        for engine in self.engines:
            if hasattr(engine, 'webview') and engine.webview:
                local_x = x - engine.mon['x']
                local_y = y - engine.mon['y']
                
                if 0 <= local_x <= engine.mon['w'] and 0 <= local_y <= engine.mon['h']:
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
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage('/').percent
        }
        json_stats = json.dumps(stats)
        for engine in self.engines:
            if hasattr(engine, 'webview') and engine.webview is not None:
                script = f"if (window.updateStats) {{ updateStats({json_stats}); }}"
                engine.webview.run_javascript(script, None, None, None)
        return True 

    def load_config(self):
        # --- PORTABILITY FIX: Ensure config.json is found relative to main.py ---
        config_path = os.path.join(BASE_DIR, "config.json")
        default_html = os.path.join(BASE_DIR, "presets", "circle", "circle.html")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception: pass
            
        return {
            "primary_source": default_html,
            "secondary_source": default_html
        }

    def save_config(self):
        config_path = os.path.join(BASE_DIR, "config.json")
        try:
            with open(config_path, "w") as f:
                json.dump(self.config, f, indent=4)
            print("Wallpapery: Config saved to disk.")
        except Exception as e:
            print(f"Wallpapery: Error saving config: {e}")

    def setup_monitor(self, mon_data):
        engine = MintpaperEngine(mon_data)
        self.engines.append(engine)
        
        key = "primary_source" if mon_data['is_primary'] else "secondary_source"
        path = self.config.get(key)

        if path and os.path.exists(path):
            if path.lower().endswith('.html'):
                print(f"Wallpapery: Loading HTML Source on Monitor {mon_data['id']}: {path}")
                engine.load_html(path)
            else:
                print(f"Wallpapery: Loading Video Source on Monitor {mon_data['id']}: {path}")
                engine.load_video(path)

        GLib.timeout_add(200, self.force_lower_engine, engine)
        GLib.timeout_add(1000, self.force_lower_engine, engine)
        GLib.timeout_add(3000, self.force_lower_engine, engine)

    def force_lower_engine(self, engine):
        if engine.window.get_window():
            engine.window.set_transient_for(None)
            engine.window.set_keep_below(True)
            engine.window.get_window().lower()
        return False

    def reload_engines(self):
        print("Wallpapery: Hot-reloading sources...")
        for engine in self.engines:
            engine.window.destroy()
        self.engines = []
        for m in self.audio_ctrl.monitors:
            m['was_muted'] = None
        
        temp_scanner = AudioController(engines=[])
        for mon_data in temp_scanner.monitors:
            self.setup_monitor(mon_data)
        
        self.audio_ctrl.engines = self.engines
        self.audio_ctrl.start()

    def update_loop(self):
        try:
            self.audio_ctrl.update()
        except Exception as e:
            print(f"Wallpapery: Audio update error: {e}")
        return True

if __name__ == "__main__":
    app = WallpaperyApp()
    print("Wallpapery: Active. Press Ctrl+C to exit.")
    Gtk.main()