import subprocess
import time
from gi.repository import Gdk

class AudioController:
    def __init__(self, engines=None):
        # We now track a list of MintpaperEngine instances instead of players
        self.engines = engines if engines is not None else []
        
        self.pause_threshold = 0.99
        self.area_threshold_percent = 0.001 
        self.last_check_time = 0
        self.check_cooldown = 0.5
        
        self.monitors = []
        self._detect_monitors()

    def _detect_monitors(self):
        """Scans the system to map every connected monitor's coordinates."""
        display = Gdk.Display.get_default()
        n_monitors = display.get_n_monitors()
        
        for i in range(n_monitors):
            monitor = display.get_monitor(i)
            geometry = monitor.get_geometry()
            
            mon_data = {
                "id": i,
                "x": geometry.x,
                "y": geometry.y,
                "w": geometry.width,
                "h": geometry.height,
                "area": geometry.width * geometry.height,
                "is_primary": monitor.is_primary(),
                "was_muted": None 
            }
            self.monitors.append(mon_data)

    def _get_monitor_overlap(self, wx, wy, ww, wh, monitor):
        """Calculates window area with robust boundary checking."""
        win_right = wx + ww
        win_bottom = wy + wh
        mon_right = monitor['x'] + monitor['w']
        mon_bottom = monitor['y'] + monitor['h']

        overlap_x_start = max(wx, monitor['x'])
        overlap_x_end = min(win_right, mon_right)
        overlap_y_start = max(wy, monitor['y'])
        overlap_y_end = min(win_bottom, mon_bottom)
        
        w = max(0, overlap_x_end - overlap_x_start)
        h = max(0, overlap_y_end - overlap_y_start)
        return w * h

    def update(self):
        current_time = time.time()
        if current_time - self.last_check_time < self.check_cooldown:
            return
        self.last_check_time = current_time

        if not self.engines:
            return

        try:
            output = subprocess.check_output(["wmctrl", "-lG"], encoding="utf-8", stderr=subprocess.DEVNULL)
            window_lines = output.strip().split('\n')

            current_coverage = {m['id']: 0 for m in self.monitors}
            
            for line in window_lines:
                parts = line.split()
                if len(parts) < 6: continue
                wid, wx, wy, ww, wh = parts[0], int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])

                for m in self.monitors:
                    area = self._get_monitor_overlap(wx, wy, ww, wh, m)
                    coverage = area / m['area']
                    if coverage > self.area_threshold_percent:
                        if not self._is_invalid_window(wid):
                            current_coverage[m['id']] = max(current_coverage[m['id']], coverage)

            for m in self.monitors:
                mid = m['id']
                coverage = current_coverage[mid]

                should_mute = current_coverage[mid] > self.area_threshold_percent

                should_pause = coverage > self.pause_threshold

                if should_mute != m['was_muted']:
                    # Find the engine that belongs to this monitor
                    for engine in self.engines:
                        if engine.mon['id'] == mid:
                            engine.set_muted(should_mute) # Call the unified method

                        if engine.mon.get("performance mode", True):
                            if should_pause != m.get('was_paused'):
                                engine.set_paused(should_pause)
                                m['was_paused'] = should_pause
                    
                    m['was_muted'] = should_mute
                    status = "MUTED" if should_mute else "UNMUTED"
                    print(f"Mintpaper: Monitor {mid} {status}")
                
        except Exception as e:
            print(f"Mintpaper: Audio logic error: {e}")

    def _is_invalid_window(self, wid):
        try:
            state = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_STATE"], encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_STATE_HIDDEN" in state: return True
            w_type = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_WINDOW_TYPE"], encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_WINDOW_TYPE_DESKTOP" in w_type or "_NET_WM_WINDOW_TYPE_DOCK" in w_type: return True
            stats = subprocess.check_output(["xwininfo", "-id", wid, "-stats"], encoding="utf-8", stderr=subprocess.DEVNULL)
            return "IsViewable" not in stats
        except: return True

    def start(self):
        """Ensure all engines start unmuted."""
        for m in self.monitors:
            m['was_muted'] = None


        for engine in self.engines:
            try:
                engine.set_muted(False)
            except: pass