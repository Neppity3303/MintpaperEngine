import subprocess
import time
from gi.repository import Gdk

class AudioController:
    def __init__(self, player):
        self.player = player
        
        # --- 1. Define Settings First ---
        self.area_threshold_percent = 0.01 
        self.last_check_time = 0
        self.check_cooldown = 0.5
        self.was_muted = None
        
        # --- 2. Now Detect Monitors ---
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
                "is_primary": monitor.is_primary()
            }
            self.monitors.append(mon_data)
            
            if mon_data["is_primary"]:
                self.primary_monitor = mon_data

        self.debug_monitors()

    def debug_monitors(self):
        """Prints a visual map of detected monitors to the console."""
        print("\n" + "="*40)
        print(" WALLPAPERY MONITOR REGISTRY")
        print("="*40)
        for m in self.monitors:
            role = "PRIMARY" if m['is_primary'] else "SECONDARY"
            print(f"Monitor {m['id']} [{role}]:")
            print(f"  -> Resolution: {m['w']}x{m['h']}")
            print(f"  -> Position:   x={m['x']}, y={m['y']}")
            print(f"  -> Threshold:  {int(m['area'] * self.area_threshold_percent)} pixels (1%)")
        print("="*40 + "\n")

    def _get_monitor_overlap(self, wx, wy, ww, wh, monitor):
        """Calculates window area specifically within a monitor's bounds."""
        overlap_x_start = max(wx, monitor['x'])
        overlap_x_end = min(wx + ww, monitor['x'] + monitor['w'])
        overlap_y_start = max(wy, monitor['y'])
        overlap_y_end = min(wy + wh, monitor['y'] + monitor['h'])
        
        w = max(0, overlap_x_end - overlap_x_start)
        h = max(0, overlap_y_end - overlap_y_start)
        return w * h

    def update(self):
        current_time = time.time()
        if current_time - self.last_check_time < self.check_cooldown:
            return
        self.last_check_time = current_time

        try:
            output = subprocess.check_output(["wmctrl", "-lG"], encoding="utf-8", stderr=subprocess.DEVNULL)
            max_primary_coverage = 0
            
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) < 6: continue
                
                wid, wx, wy, ww, wh = parts[0], int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])

                # Use the primary monitor data we stored during detection
                area = self._get_monitor_overlap(wx, wy, ww, wh, self.primary_monitor)
                coverage = area / self.primary_monitor['area']
                
                if coverage > self.area_threshold_percent:
                    if not self._is_invalid_window(wid):
                        max_primary_coverage = max(max_primary_coverage, coverage)
            
            should_mute = max_primary_coverage > self.area_threshold_percent

            if should_mute != self.was_muted:
                self.player.mute = should_mute
                status = "MUTED (Primary Covered)" if should_mute else "UNMUTED (Primary Clear)"
                print(f"Wallpapery: {status}")
                self.was_muted = should_mute
                
        except Exception:
            pass

    def _is_invalid_window(self, wid):
        """Muffin Guard & Ghost Buster."""
        try:
            state = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_STATE"], encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_STATE_HIDDEN" in state: return True
            w_type = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_WINDOW_TYPE"], encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_WINDOW_TYPE_DESKTOP" in w_type or "_NET_WM_WINDOW_TYPE_DOCK" in w_type: return True
            stats = subprocess.check_output(["xwininfo", "-id", wid, "-stats"], encoding="utf-8", stderr=subprocess.DEVNULL)
            return "IsViewable" not in stats
        except:
            return True

    def start(self):
        try:
            self.player.volume = 100
            self.player.mute = False
        except:
            pass