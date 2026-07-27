import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from pathlib import Path
import mpv

from engine.base import MintpaperPlugin, MintpaperEvents

class Mp4Plugin(MintpaperPlugin):
    
    @staticmethod
    def get_plugin_info():
        return {
            'display_name': 'MP4 Player',
            'description': 'Hardware-accelerated MP4 wallpaper using MPV'
        }

    @staticmethod
    def get_plugin_settings_info():
        return [
            {
                'property': ['muted', 'volume'],
                'default': [True, 50],
                'control_type': 'CHECKBOX_AND_SLIDER',
                'checkbox_settings': {'label': 'Mute'},
                'slider_settings': {'lower': 0, 'upper': 100},
                'category': 'Audio'
            },
        ]

    def __init__(self, engine, settings):
        super().__init__(engine, settings)
        self.player = None
        self.video_widget = None

    def setup(self):
        video_path = self.settings.get('video_path', '')
        if not video_path:
            print("Mintpaper: Mp4Plugin failed - No video_path provided.")
            return False

        file_path = Path(video_path).absolute()
        if not file_path.is_file():
            print(f"Mintpaper: Mp4Plugin failed - File not found: {file_path}")
            return False

        # Create a blank GTK canvas to draw the video on
        self.video_widget = Gtk.DrawingArea()
        
        # We MUST wait for the widget to be "realized" (drawn by X11) 
        # before we can get its window ID to pass to MPV.
        self.video_widget.connect("realize", self._on_realize)
        
        self.engine.container.pack_start(self.video_widget, True, True, 0)
        self.engine.window.show_all()

        return True

    def _on_realize(self, widget):
        # Grab the X11 Window ID
        xid = widget.get_window().get_xid()
        
        # Initialize MPV and tell it to render directly to our GTK widget's XID
        self.player = mpv.MPV(wid=str(xid), loop="inf", hwdec="auto")
        
        # Apply initial settings
        self.player.mute = self.settings.get('muted', True)
        self.player.volume = self.settings.get('volume', 50)
        
        # Start playback
        file_path = Path(self.settings.get('video_path', '')).absolute()
        self.player.play(str(file_path))

    def teardown(self):
        if self.player:
            self.player.terminate()
            self.player = None
        if self.video_widget:
            self.video_widget.destroy()
            self.video_widget = None

    def handle_event(self, event_type, data):
        # If the player hasn't initialized yet, drop the event
        if not self.player:
            return

        if event_type == MintpaperEvents.SET_PAUSED:
            self.player.pause = data.get('should_pause', False)
        elif event_type == MintpaperEvents.SET_MUTED:
            self.player.mute = data.get('should_mute', True)
        elif event_type == "SET_VOLUME":
            self.player.volume = data.get('volume', 50)