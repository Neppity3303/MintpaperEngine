import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, Gdk, WebKit2
import os
import mpv

class MintpaperEngine:
    def __init__(self, mon_data):
        self.mon = mon_data
        self.window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
        
        # Enable transparency support
        screen = self.window.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.window.set_visual(visual)

        # STABLE LAYERING: DESKTOP ensures icons are on top
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
        
        self.player = None
        self.webview = None

    def load_video(self, video_path):
        """Restored the missing video loading method."""
        for child in self.container.get_children():
            self.container.remove(child)
            
        drawing_area = Gtk.DrawingArea()
        self.container.pack_start(drawing_area, True, True, 0)
        
        # We must show the window so the DrawingArea gets an X11 ID (wid)
        self.window.show_all()
        
        wid = drawing_area.get_window().get_xid()
        self.player = mpv.MPV(wid=wid, loop=True, hwdec="auto", mute=True)
        self.player.play(video_path)
        return self.player

    def load_html(self, html_path):
        for child in self.container.get_children():
            self.container.remove(child)
            
        self.webview = WebKit2.WebView()
        self.webview.set_background_color(Gdk.RGBA(0, 0, 0, 0))
        
        settings = self.webview.get_settings()
        settings.set_allow_file_access_from_file_urls(True)
        settings.set_enable_2d_canvas_acceleration(True)
        settings.set_media_playback_allows_inline(True)
        settings.set_media_playback_requires_user_gesture(False)
        
        self.container.pack_start(self.webview, True, True, 0)
        self.window.show_all()
        
        file_url = "file://" + os.path.abspath(html_path)
        self.webview.load_uri(file_url)
        return self.webview

    def set_muted(self, should_mute):
        if self.player:
            self.player.mute = should_mute
        elif self.webview:
            # This mutes the entire WebKit process at the browser level
            self.webview.set_is_muted(should_mute)
    
    def set_paused(self, should_pause):
        if self.player:
            # If using MPV/Video
            self.player.pause = should_pause
        elif self.webview:
            # 1. Hardware Pause: Stop the WebKit process from rendering
            # This is the 'Nuclear' pause that saves CPU
            if hasattr(self.webview, 'set_is_paused'):
                self.webview.set_is_paused(should_pause)
            
            # 2. JS Fallback: Also tell the JS to stop any loops/animations
            val = "true" if should_pause else "false"
            script = f"""
                if (window.mintpaper_paused !== {val}) {{
                    window.mintpaper_paused = {val};
                    document.querySelectorAll('video').forEach(v => {val} ? v.pause() : v.play());
                    // Custom event for wallpaper creators to listen to
                    window.dispatchEvent(new CustomEvent('wallpaperPause', {{ detail: {val} }}));
                }}
            """
            self.webview.run_javascript(script, None, None, None)