import subprocess
import time
from gi.repository import Gdk
from engine.base import MintpaperEvents

class MintpaperTracker:
    def __init__(self, engines=None):
        self.engines = engines if engines is not None else []
        self.start_time = time.time()
        
        # 95% coverage triggers the Coma Script. 0.1% triggers Mute.
        self.pause_threshold = 0.95  
        self.area_threshold_percent = 0.001 
        self.last_check_time = 0
        self.check_cooldown = 0.5 
        
        self.monitors = []
        self._detect_monitors()

    def _detect_monitors(self):
        """Maps out the physical boundaries of all connected displays."""
        display = Gdk.Display.get_default()
        if not display:
            return

        for i in range(display.get_n_monitors()):
            monitor = display.get_monitor(i)
            geo = monitor.get_geometry()
            self.monitors.append({
                "id": i,
                "area": geo.width * geo.height,
                "geometry": {"x": geo.x, "y": geo.y, "w": geo.width, "h": geo.height},
                "was_paused": False,
                "was_muted": False
            })

    def update(self):
        """The main loop. Calculates window occlusion and dispatches events."""
        current_time = time.time()
        if current_time - self.last_check_time < self.check_cooldown:
            return
        self.last_check_time = current_time

        if not self.engines:
            return

        # Bulletproof subprocess call to avoid crashes if X11 stutters
        try:
            output = subprocess.check_output(
                ["wmctrl", "-lG"], 
                encoding="utf-8", 
                stderr=subprocess.DEVNULL,
                timeout=0.2 
            )
            window_lines = output.strip().split('\n')
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return

        current_coverage = {m['id']: 0 for m in self.monitors}
        
        # Collect our own engine X11 Window IDs so we don't track ourselves
        engine_wids = set()
        for e in self.engines:
            if e.window and e.window.get_window():
                engine_wids.add(hex(e.window.get_window().get_xid()))

        for line in window_lines:
            parts = line.split()
            if len(parts) < 6: 
                continue
                
            wid = parts[0]
            if wid in engine_wids: 
                continue
            
            # Parse X11 geometry: X, Y, Width, Height
            wx, wy, ww, wh = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])

            for m in self.monitors:
                overlap = self._calculate_overlap(wx, wy, ww, wh, m['geometry'])
                coverage = overlap / m['area']
                
                # Only check validity if it actually covers the screen to save CPU cycles
                if coverage > self.area_threshold_percent:
                    if not self._is_invalid_window(wid):
                        current_coverage[m['id']] = max(current_coverage[m['id']], coverage)

        self._dispatch_state_changes(current_coverage)

    

    def _calculate_overlap(self, wx, wy, ww, wh, m_geo):
        """Standard AABB intersection math to find overlapping area."""
        overlap_x = max(0, min(wx + ww, m_geo['x'] + m_geo['w']) - max(wx, m_geo['x']))
        overlap_y = max(0, min(wy + wh, m_geo['y'] + m_geo['h']) - max(wy, m_geo['y']))
        return overlap_x * overlap_y

    def _dispatch_state_changes(self, current_coverage):
        """Compares new state to old state and fires events ONLY if changed."""
        for m in self.monitors:
            mid = m['id']
            coverage = current_coverage[mid]
            
            should_pause = coverage > self.pause_threshold
            should_mute = coverage > self.area_threshold_percent

            # Fire PAUSE events via the Contract
            if should_pause != m['was_paused']:
                m['was_paused'] = should_pause
                for engine in self.engines:
                    if engine.mon.get('id') == mid:
                        engine.handle_event(MintpaperEvents.SET_PAUSED, {"should_pause": should_pause})

            # Fire MUTE events via the Contract
            if should_mute != m['was_muted']:
                m['was_muted'] = should_mute
                for engine in self.engines:
                    if engine.mon.get('id') == mid:
                        engine.handle_event(MintpaperEvents.SET_MUTED, {"should_mute": should_mute})

    def _is_invalid_window(self, wid):
        """Checks if a window is minimized or a desktop widget."""
        try:
            state = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_STATE"], encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_STATE_HIDDEN" in state: return True
            
            w_type = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_WINDOW_TYPE"], encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_WINDOW_TYPE_DESKTOP" in w_type or "_NET_WM_WINDOW_TYPE_DOCK" in w_type: return True
            
            return False
        except Exception:
            return True