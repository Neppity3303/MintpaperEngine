import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, GLib, Gdk, WebKit2
from pathlib import Path
import json

from engine.base import MintpaperPlugin, MintpaperEvents

class WebviewPlugin(MintpaperPlugin):
    
    @staticmethod
    def get_plugin_info():
        return {
            'display_name': 'Webview',
            'description': 'Display a local HTML page with JavaScript interactivity'
        }

    @staticmethod
    def get_plugin_settings_info():
        # This acts as the blueprint for the 0.40.00 Dynamic UI Control Panel
        return [
            {
                'property': ['muted', 'volume'],
                'default': [True, 50],
                'control_type': 'CHECKBOX_AND_SLIDER',
                'checkbox_settings': {'label': 'Mute'},
                'slider_settings': {'lower': 0, 'upper': 100},
                'category': 'Audio'
            },
            {
                'property': 'html_path',
                'default': '',
                'control_type': 'FILE_PATH',
                'label': 'Wallpaper File'
            },
            {
                'property': 'fps_limit',
                'default': 60,
                'control_type': 'SLIDER',
                'settings': {'lower': 15, 'upper': 144},
                'label': 'FPS Limit'
            }
        ]

    def __init__(self, engine, settings):
        super().__init__(engine, settings)
        self.webview = None

    def setup(self):
        # Using self.settings to avoid the scoping bug from the fork
        html_path = self.settings.get('html_path', '')
        if not html_path:
            print("Mintpaper: WebviewPlugin failed - No html_path provided.")
            return False

        file_path = Path(html_path).absolute()
        if not file_path.is_file():
            print(f"Mintpaper: WebviewPlugin failed - File not found: {file_path}")
            return False

        self.webview = WebKit2.WebView()
        self.webview.set_background_color(Gdk.RGBA(0, 0, 0, 0))
        
        webview_settings = self.webview.get_settings()
        webview_settings.set_allow_file_access_from_file_urls(True)
        webview_settings.set_enable_2d_canvas_acceleration(True)
        webview_settings.set_media_playback_allows_inline(True)
        webview_settings.set_media_playback_requires_user_gesture(False)
        
        self.engine.container.pack_start(self.webview, True, True, 0)
        self.engine.window.show_all()

        # Apply initial audio state
        self.webview.set_is_muted(self.settings.get('muted', True))
        
        # Load the local file
        self.webview.load_uri(file_path.as_uri())

        # Apply initial JS parameters once loaded
        fps_limit = self.settings.get('fps_limit', 60)
        volume = self.settings.get('volume', 50)
        init_script = f"if(window.setFPS) {{ setFPS({fps_limit}); if(window.updateVolume) {{ updateVolume({volume}); }}}}"
        GLib.timeout_add(1000, lambda: self.webview.run_javascript(init_script, None, None, None))

        return True

    def teardown(self):
        if self.webview:
            self.webview.destroy()
            self.webview = None

    def handle_event(self, event_type, data):
        # The central router for all incoming engine commands
        if not self.webview:
            return

        if event_type == MintpaperEvents.SET_PAUSED:
            self._set_paused(data.get('should_pause', False))
        elif event_type == MintpaperEvents.SET_MUTED:
            self._set_muted(data.get('should_mute', True))
        elif event_type == "SET_VOLUME":
            self._set_volume(data.get('volume', 0))
        elif event_type == "MOUSE_MOVE":
            self._on_mouse_move(data)
        elif event_type == "MOUSE_CLICK":
            self._on_mouse_click(data)

    # --- Internal Event Handlers ---

    def _set_paused(self, should_pause):
        # 1. Native WebKit Rendering Pause
        if hasattr(self.webview, 'set_is_paused'):
            self.webview.set_is_paused(should_pause)

        # 2. The Coma Script: Aggressive JS Hijack
        val = "true" if should_pause else "false"
        script = f"""
        (function() {{
            if (window._mp_controlled === undefined) {{
                window._mp_raf = window.requestAnimationFrame;
                window._mp_controlled = true;
            }}

            if ({val}) {{
                // PAUSE: Kill the animation loop
                window.requestAnimationFrame = function() {{ return 0; }};
                document.body.style.animationPlayState = 'paused';
                document.querySelectorAll('video, audio').forEach(m => m.pause());
            }} else {{
                // RESUME: Restore the loop
                window.requestAnimationFrame = window._mp_raf;
                document.body.style.animationPlayState = 'running';
                document.querySelectorAll('video, audio').forEach(m => m.play());
            }}
            
            // Dispatch standard event for custom wallpaper logic
            window.dispatchEvent(new CustomEvent('wallpaperPause', {{ detail: {val} }}));
        }})();
        """
        self.webview.run_javascript(script, None, None, None)

    def _set_muted(self, should_mute):
        self.webview.set_is_muted(should_mute)

    def _set_volume(self, volume):
        script = f"if(window.updateVolume) {{ updateVolume({volume}); }}"
        GLib.idle_add(self.webview.run_javascript, script, None, None, None)

    def _on_mouse_move(self, data):
        local_x = data.get('local_x', 0)
        local_y = data.get('local_y', 0)
        script = f"if(window.updateMouse) {{ window.updateMouse({local_x}, {local_y}); }}"
        GLib.idle_add(self.webview.run_javascript, script, None, None, None)

    def _on_mouse_click(self, data):
        val = "true" if data.get('clicked') else "false"
        script = f"if(window.updateClick) {{ window.updateClick({val}); }}"
        GLib.idle_add(self.webview.run_javascript, script, None, None, None)