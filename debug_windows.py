from ewmh import EWMH
import Xlib.display

def diagnostic_scan():
    ewmh = EWMH()
    all_clients = ewmh.getClientList()
    print(f"{'WINDOW NAME':<30} | {'CLASS':<20} | {'X':<5} | {'WIDTH':<6}")
    print("-" * 70)

    for client in all_clients:
        try:
            name = client.get_wm_name()
            if isinstance(name, bytes): name = name.decode('utf-8', errors='ignore')
            
            wm_class = client.get_wm_class()
            class_str = " ".join(wm_class) if wm_class else "None"
            
            geom = client.get_geometry()
            
            # Check if it's on your primary monitor (X < 2560)
            if 0 <= geom.x < 2560 and geom.width > 50:
                print(f"{str(name)[:30]:<30} | {class_str[:20]:<20} | {geom.x:<5} | {geom.width:<6}")
        except:
            continue

if __name__ == "__main__":
    diagnostic_scan()