import os
import gi
import json
gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, GLib
from gi.repository import AyatanaAppIndicator3 as AppIndicator
import signal
import sys
from pynput import mouse
import psutil

from engine.window import MintpaperEngine
from engine.display import sync_config
from engine.tracker import MintpaperTracker
from plugins.webview import WebviewPlugin
from plugins.mp4 import Mp4Plugin
from ui.editor import MintpaperEditor


class MintpaperApp:
    def __init__(self):
        self.config = sync_config()
        self.engines = []
        
        for mon_data in self.config.get('monitors', []):
            engine = MintpaperEngine(mon_data)
            
            file_path = mon_data.get("active_preset_path", "")
            ext = file_path.lower().split('.')[-1] if file_path else ""

            if ext == 'mp4':
                settings = {
                    "video_path": file_path,
                    "muted": mon_data.get("is_muted", True),
                    "volume": mon_data.get("volume", 50),
                    "fps_limit": mon_data.get("fps_limit", 60)
                }
                engine.load_plugin(Mp4Plugin, settings)
            elif ext == 'html':
                settings = {
                    "html_path": file_path,
                    "muted": mon_data.get("is_muted", True),
                    "volume": mon_data.get("volume", 50),
                    "fps_limit": mon_data.get("fps_limit", 60)
                }
                engine.load_plugin(WebviewPlugin, settings)

            self.engines.append(engine)

        self.tracker = MintpaperTracker(self.engines)

        GLib.timeout_add(500, self.run_tracker)
        
        # NEW: Start the global mouse listener in a background thread
        self.mouse_listener = mouse.Listener(on_move=self.on_mouse_move, on_click=self.on_mouse_click)
        self.mouse_listener.start()

        #CPU Tracker
        psutil.cpu_percent(interval=None)
        GLib.timeout_add_seconds(2, self.broadcast_stats)
        
        # Launch the temporary UI
        self.ui = MintpaperEditor(self)
        self.setup_tray()


    def load_preset_to_monitor(self, mon_idx, file_path):
        print(f"Engine: Routing {file_path} to Monitor {mon_idx}")

        self.config['monitors'][mon_idx]['active_preset_path'] = file_path

        with open('config.json', 'w') as f:
            json.dump(self.config, f, indent=4)

        ext = file_path.lower().split('.')[-1]

        if ext == 'mp4':
            settings = {
                "video_path": file_path,
                "muted": self.config['monitors'][mon_idx].get("is_muted", True),
                "volume": self.config['monitors'][mon_idx].get("volume", 50),
                "fps_limit": self.config['monitors'][mon_idx].get("fps_limit", 60)
            }
            self.engines[mon_idx].load_plugin(Mp4Plugin, settings)
        elif ext == 'html':
            settings = {
                "html_path": file_path,
                "muted": self.config['monitors'][mon_idx].get("is_muted", True),
                "volume": self.config['monitors'][mon_idx].get("volume", 50),
                "fps_limit": self.config['monitors'][mon_idx].get("fps_limit", 60)
            }
            self.engines[mon_idx].load_plugin(WebviewPlugin, settings)

    def setup_tray(self):

        icon_path = os.path.abspath("assets/mpe.png")
        self.indicator= AppIndicator.Indicator.new(
            "mintpaper-engine",
            icon_path,
            AppIndicator.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_tray_menu())

    def build_tray_menu(self):
        menu = Gtk.Menu()

        item_editor = Gtk.MenuItem(label="Open Editor")
        item_editor.connect("activate", self.show_editor)
        menu.append(item_editor)

        item_quit = Gtk.MenuItem(label="Quit Mintpaper")
        item_quit.connect("activate", self.quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def show_editor(self, source):
        self.ui.show_all()
        self.ui.present()

    # NEW: Capture global mouse movement
    def on_mouse_move(self, x, y):
        # Safely queue the event back onto the main GTK thread
        GLib.idle_add(self._dispatch_mouse_events, x, y)


    def on_mouse_click(self, x, y, button, pressed):
        if button == mouse.Button.left:
            GLib.idle_add(self._dispatch_mouse_click, x, y, pressed)

    def _dispatch_mouse_click(self, x, y, pressed):
        for engine in self.engines:
            geo = engine.mon.get('geometry')

            if (geo['x'] <= x <= geo['x'] + geo['w'] and geo['y'] <= y <= geo['y'] + geo['h']):
                engine.handle_event("MOUSE_CLICK", {"clicked": pressed})

            return False

    # NEW: Translate coordinates and broadcast to the router
    def _dispatch_mouse_events(self, x, y):
        for engine in self.engines:
            geo = engine.mon.get('geometry')
            
            # Translate global OS coordinates into local monitor coordinates
            local_x = x - geo['x']
            local_y = y - geo['y']
            
            engine.handle_event("MOUSE_MOVE", {"local_x": local_x, "local_y": local_y})
        
        # Returning False tells GLib.idle_add to run this exactly once per event
        return False 

    def broadcast_stats(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        for engine in self.engines:
            engine.handle_event("SYS_STATS", {"cpu": cpu, "ram": ram})
        return True

    def run_tracker(self):
        self.tracker.update()
        return True

    def quit(self, *args):
        # NEW: Cleanly stop the background mouse thread on exit
        if hasattr(self, 'mouse_listener'):
            self.mouse_listener.stop()
            
        for engine in self.engines:
            if engine.plugin:
                engine.plugin.teardown()
            engine.window.destroy()
        Gtk.main_quit()
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, self.quit)
        Gtk.main()

if __name__ == "__main__":
    app = MintpaperApp()
    app.run()