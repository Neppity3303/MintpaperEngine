import subprocess
import time

class AudioController:
    def __init__(self, player):
        self.player = player
        
        # --- Visual Mapping (Primary Monitor) ---
        self.screen_width = 2560
        self.screen_height = 1440
        self.primary_x_start = 0  # Assuming primary is on the left
        self.primary_y_start = 0
        self.total_screen_area = self.screen_width * self.screen_height
        
        # --- Threshold ---
        self.area_threshold_percent = 0.01 
        
        # --- State Tracking ---
        self.last_check_time = 0
        self.check_cooldown = 0.5
        self.was_muted = None

    def start(self):
        print("Wallpapery: AudioController started with Visual Mapping (Primary Monitor).")
        self._force_unmute()

    def _force_unmute(self):
        try:
            if hasattr(self.player, 'volume'):
                self.player.volume = 100
            self.player.mute = False
        except:
            pass

    def _is_invalid_window(self, wid):
        """Muffin Guard & Ghost Buster."""
        try:
            # 1. Check for Hidden state
            state = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_STATE"], 
                                            encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_STATE_HIDDEN" in state:
                return True

            # 2. Check for Window Type (Ignore Desktops/Panels)
            w_type = subprocess.check_output(["xprop", "-id", wid, "_NET_WM_WINDOW_TYPE"], 
                                             encoding="utf-8", stderr=subprocess.DEVNULL)
            if "_NET_WM_WINDOW_TYPE_DESKTOP" in w_type or "_NET_WM_WINDOW_TYPE_DOCK" in w_type:
                return True

            # 3. Check Viewable status
            stats = subprocess.check_output(["xwininfo", "-id", wid, "-stats"], 
                                            encoding="utf-8", stderr=subprocess.DEVNULL)
            if "IsViewable" not in stats:
                return True

            return False
        except:
            return True

    def update(self):
        current_time = time.time()
        if current_time - self.last_check_time < self.check_cooldown:
            return
        self.last_check_time = current_time

        try:
            # wmctrl -lG provides: ID, Desktop, X, Y, W, H, Host, Title
            output = subprocess.check_output(["wmctrl", "-lG"], encoding="utf-8", stderr=subprocess.DEVNULL)
            max_primary_area = 0
            
            for line in output.strip().split('\n'):
                parts = line.split()
                if len(parts) < 6: continue
                
                wid = parts[0]
                win_x = int(parts[2])
                win_y = int(parts[3])
                win_w = int(parts[4])
                win_h = int(parts[5])

                # --- Visual Mapping Logic ---
                # Check if the window is within the bounds of the primary monitor
                is_on_primary = (
                    win_x < self.screen_width and 
                    (win_x + win_w) > self.primary_x_start and
                    win_y < self.screen_height and
                    (win_y + win_h) > self.primary_y_start
                )

                if is_on_primary:
                    # Only calculate the area that is actually ON the primary monitor
                    overlap_w = min(win_x + win_w, self.screen_width) - max(win_x, self.primary_x_start)
                    overlap_h = min(win_y + win_h, self.screen_height) - max(win_y, self.primary_y_start)
                    
                    if overlap_w > 0 and overlap_h > 0:
                        area = overlap_w * overlap_h
                        
                        # If significant, verify it isn't a ghost or muffin component
                        if area > (self.total_screen_area * self.area_threshold_percent):
                            if not self._is_invalid_window(wid):
                                max_primary_area = max(max_primary_area, area)
            
            coverage = max_primary_area / self.total_screen_area
            should_mute = coverage > self.area_threshold_percent

            if should_mute != self.was_muted:
                if should_mute:
                    self.player.mute = True
                    print(f"Wallpapery: Muted (Primary covered {coverage:.1%})")
                else:
                    self._force_unmute()
                    print("Wallpapery: Unmuted (Primary clear)")
                
                self.was_muted = should_mute
                
        except Exception as e:
            pass