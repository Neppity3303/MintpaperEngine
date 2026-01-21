import time
from ewmh import EWMH

def diagnose():
    manager = EWMH()
    print("--- Wallpapery Diagnostic ---")
    
    # 1. Check for the Desktop
    desktop_windows = manager.getClientList()
    print(f"Found {len(desktop_windows)} total windows.")
    
    # 2. Monitor Loop
    print("Monitoring window changes for 10 seconds...")
    print("Try opening and closing a folder or terminal now.")
    
    for _ in range(20):
        active_window = manager.getActiveWindow()
        if active_window:
            name = active_window.get_wm_name()
            # If the name is None, it's often the desktop/root
            print(f"Active Window: {name if name else 'Desktop/Root'}")
        else:
            print("Active Window: Unknown")
        
        time.sleep(0.5)

if __name__ == "__main__":
    diagnose()