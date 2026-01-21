import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

def create_wallpaper_window(window):
    # This hint is the specific one that worked for icons
    window.set_type_hint(Gdk.WindowTypeHint.DESKTOP)
    
    # Standard background behavior
    window.set_keep_below(True)
    window.set_decorated(False)
    window.set_accept_focus(False)
    window.set_skip_taskbar_hint(True)
    
    # 2560x1440 for your primary monitor
    window.set_default_size(2560, 1440)
    window.move(0, 0)
    
    window.show_all()
    
    # A single, simple lower command
    if window.get_window():
        window.get_window().lower()