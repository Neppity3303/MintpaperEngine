import gi
import json
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import signal
import sys

from engine.window import MintpaperEngine
from engine.display import sync_config
from engine.tracker import MintpaperTracker
from plugins.webview import WebviewPlugin

class QuickUI(Gtk.Window):
    """A temporary 0.10.00 UI for the video showcase."""
    def __init__(self, app_ref):
        super().__init__(title="Mintpaper Temp UI")
        self.app_ref = app_ref
        self.set_default_size(300, 100)
        self.set_border_width(10)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(box)
        
        label = Gtk.Label(label="Select HTML Preset:")
        box.pack_start(label, True, True, 0)
        
        # Native GTK File picker
        self.file_chooser = Gtk.FileChooserButton(title="Choose a preset", action=Gtk.FileChooserAction.OPEN)
        self.file_chooser.connect("file-set", self.on_file_selected)
        box.pack_start(self.file_chooser, True, True, 0)
        
        self.show_all()

    def on_file_selected(self, widget):
        file_path = widget.get_filename()
        if file_path:
            print(f"UI: Loading new preset: {file_path}")
            
            # 1. Update the config dict for the first monitor
            self.app_ref.config['monitors'][0]['active_preset_path'] = file_path
            
            # 2. Save it to disk so it remembers for next time
            with open("config.json", "w") as f:
                json.dump(self.app_ref.config, f, indent=4)
            
            # 3. Hot-reload the engine with the new file
            settings = {
                "html_path": file_path,
                "muted": True,
                "volume": 50,
                "fps_limit": 60
            }
            # Assuming you want to change the primary monitor (engine 0)
            self.app_ref.engines[0].load_plugin(WebviewPlugin, settings)


class MintpaperApp:
    def __init__(self):
        self.config = sync_config()
        self.engines = []
        
        for mon_data in self.config.get('monitors', []):
            engine = MintpaperEngine(mon_data)
            
            settings = {
                "html_path": mon_data.get("active_preset_path", ""),
                "muted": True,
                "volume": 50,
                "fps_limit": mon_data.get("fps_limit", 60)
            }
            
            engine.load_plugin(WebviewPlugin, settings)
            self.engines.append(engine)

        self.tracker = MintpaperTracker(self.engines)
        GLib.timeout_add(500, self.run_tracker)
        
        # Launch the temporary UI
        self.ui = QuickUI(self)

    def run_tracker(self):
        self.tracker.update()
        return True

    def quit(self, *args):
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