import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
import mpv
import os
import json
import sys

# Ensure logs appear in the terminal immediately for debugging
os.environ['PYTHONUNBUFFERED'] = '1'

try:
    from engine.window import create_wallpaper_window
    from engine.audio import AudioController
except ImportError as e:
    print(f"Error: Could not find engine folder or files. {e}")
    sys.exit(1)

class WallpaperyApp:
    def __init__(self):
        print("Wallpapery: Initializing engine...")
        
        # 1. Load Configuration
        self.config = self.load_config()
        
        # 2. Setup GTK Window
        self.window = Gtk.Window()
        self.drawing_area = Gtk.DrawingArea()
        self.window.add(self.drawing_area)
        
        # 3. Connect events
        self.window.connect("realize", self.on_realize)
        self.window.connect("destroy", Gtk.main_quit)
        
        # 4. Apply the simple desktop layering logic
        create_wallpaper_window(self.window)

    def load_config(self):
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading config.json: {e}")
        
        return {
            "video_path": os.path.expanduser("~/Videos/wallpaper2.mp4")
        }

    def on_realize(self, widget):
        print("Wallpapery: Window realized. Attaching Media Player...")
        window_id = widget.get_window().get_xid()
        
        try:
            # Using pulse as the bridge for PipeWire
            self.player = mpv.MPV(
                wid=window_id, 
                loop=True, 
                hwdec="auto", 
                ao="pulse"
            )
            
            # Start silent to let the AudioController trigger the first unmute
            self.player.volume = 0
            print("Wallpapery: MPV started at volume 0.")
            
        except Exception as e:
            print(f"Failed to initialize MPV: {e}")
            return

        # Initialize Audio Controller
        self.audio_ctrl = AudioController(self.player)
        self.audio_ctrl.start()
        
        # Load and play the video
        v_path = self.config.get("video_path")
        if os.path.exists(v_path):
            print(f"Wallpapery: Loading video: {v_path}")
            self.player.play(v_path)
        else:
            print(f"Wallpapery: Error - Video not found at {v_path}")
        
        # Start the audio monitoring loop (500ms intervals)
        GLib.timeout_add(500, self.update_audio)

    def update_audio(self):
        try:
            if hasattr(self, 'audio_ctrl'):
                self.audio_ctrl.update()
        except Exception as e:
            print(f"Wallpapery: Audio loop error: {e}")
        return True

if __name__ == "__main__":
    app = WallpaperyApp()
    print("Wallpapery: Active. Monitoring Primary Monitor...")
    print("Press Ctrl+C to exit.")
    Gtk.main()