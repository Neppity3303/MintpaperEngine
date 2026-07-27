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

class QuickUI(Gtk.Window):
    """A temporary 0.10.00 UI for the video showcase."""
    def __init__(self, app_ref):
        super().__init__(title="Mintpaper Temp UI")
        self.app_ref = app_ref
        self.set_default_size(300, 100)
        self.set_border_width(10)

        self.connect("delete-event", self.on_delete_event)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(box)
        
        label = Gtk.Label(label="Select HTML or MP4 Preset:")
        box.pack_start(label, True, True, 0)
        
        # Native GTK File picker
        self.file_chooser = Gtk.FileChooserButton(title="Choose a preset", action=Gtk.FileChooserAction.OPEN)
        self.file_chooser.connect("file-set", self.on_file_selected)
        box.pack_start(self.file_chooser, True, True, 0)

        

    def on_delete_event(self, widget, event):
        self.hide()
        return True  # Prevents the window from being destroyed

    def on_file_selected(self, widget):
        file_path = widget.get_filename()
        if file_path:
            print(f"UI: Loading new preset: {file_path}")
            
            # 1. Update the config dict for the first monitor
            self.app_ref.config['monitors'][0]['active_preset_path'] = file_path
            
            # 2. Save it to disk so it remembers for next time
            with open("config.json", "w") as f:
                json.dump(self.app_ref.config, f, indent=4)

            ext = file_path.lower().split('.')[-1]

            if ext == 'mp4':
                # Load the MP4 plugin for the first monitor
                settings = {
                    "video_path": file_path,
                    "muted": True,
                    "volume": 50,
                    "fps_limit": 60
                }
                self.app_ref.engines[0].load_plugin(Mp4Plugin, settings)
            elif ext == 'html':
                # Load the Webview plugin for the first monitor
                settings = {
                    "html_path": file_path,
                    "muted": True,
                    "volume": 50,
                    "fps_limit": 60
                }
                self.app_ref.engines[0].load_plugin(WebviewPlugin, settings)


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
        self.ui = QuickUI(self)
        self.setup_tray()

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