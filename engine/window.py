import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class MintpaperEngine:
    def __init__(self, mon_data):
        self.mon = mon_data
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        
        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        self.window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
        self.window.set_keep_below(True)
        self.window.set_decorated(False)
        self.window.set_accept_focus(False)
        self.window.set_skip_taskbar_hint(True)
        
        geo = mon_data.get('geometry', mon_data) 
        self.window.move(geo['x'], geo['y'])
        self.window.resize(geo['w'], geo['h'])
        
        self.container = Gtk.Box()
        self.window.add(self.container)
        
        self.plugin = None

        # --- THE JANK TIMER (For the Dev Diary) ---
        # Wait 2000ms, then force the X11 window to the bottom of the stack
        GLib.timeout_add(2000, self._jank_push_back)

    def _jank_push_back(self):
        """The infamous wait-and-pray method."""
        if self.window.get_window():
            print("Mintpaper: 2000ms elapsed. Forcing window to background.")
            self.window.get_window().lower()
        return False # Returning False stops the timer from repeating

    def load_plugin(self, plugin_class, settings):
        if self.plugin:
            self.plugin.teardown()
            for child in self.container.get_children():
                self.container.remove(child)

        self.plugin = plugin_class(self, settings)
        if not self.plugin.setup():
            print(f"Mintpaper: Failed to load plugin {plugin_class.__name__}")
            self.plugin = None
            self.window.show_all()
        
        # --- THE HOT-SWAP LAYER FIX ---
        # Force the window back down immediately after drawing the new wallpaper
        if self.window.get_window():
            self.window.get_window().lower()

    def handle_event(self, event_type, data):
        if self.plugin:
            self.plugin.handle_event(event_type, data)