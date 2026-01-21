# Wallpapery - Linux Mint Cinnamon Wallpaper Engine Clone

A video wallpaper engine for Linux Mint Cinnamon 22.2 and 22.3.

## Features

✅ **Video Wallpaper Support** - Play MP4 videos as animated desktop wallpaper  
✅ **Audio Control** - Automatic muting when windows are active, unmutes when desktop is empty  
✅ **Hardware Acceleration** - Uses MPV with auto hwdec for smooth playback  
✅ **Ghost Mode** - Window is transparent to mouse clicks

⚠️  **Desktop Icons** - Known limitation (see below)

## Known Limitations

### Desktop Icons Not Displaying

Desktop icons (from ~/Desktop folder) do not display above the video wallpaper. This is a limitation of how Cinnamon manages the desktop layer when a fullscreen video window is active.

**Why:** In Cinnamon, desktop icon rendering is managed by Nemo, but Nemo's desktop window becomes hidden when another fullscreen window (our wallpaper) is present. This is a fundamental conflict in X11/Wayland window management.

**Workarounds:**
1. Accept the limitation - most wallpaper engines don't show desktop icons either
2. Use a file manager window for file access (Pin Nemo to taskbar)
3. Use keyboard shortcuts to access files

## Configuration

Create/edit `config.json`:

```json
{
    "video_path": "/path/to/wallpaper.mp4"
}
```

Default: `~/Videos/wallpaper2.mp4`

## Installation

```bash
cd /home/brandon/Documents/wallpapery
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
cd /home/brandon/Documents/wallpapery
source venv/bin/activate
python main.py
```

Or with virtual environment directly:

```bash
/home/brandon/Documents/wallpapery/venv/bin/python main.py
```

To run in background:

```bash
/home/brandon/Documents/wallpapery/venv/bin/python main.py > /tmp/wallpapery.log 2>&1 &
```

## Stopping

```bash
pkill -f "python.*main.py"
```

## Audio System

The audio controller automatically manages volume based on active windows:

- **Mutes** when: Terminal, browser, file manager, or other applications are active
- **Unmutes** when: Only the desktop/Cinnamon panel is active

Edit `engine/audio.py` to customize the ignore list.

## Technical Details

### Window Management

- Uses GTK 3.0 with Gdk
- Sets `_NET_WM_TYPE_HINT.DESKTOP` for proper stacking
- Uses `_NET_WM_STATE_BELOW` to stay below normal windows
- Applies input shape to make window click-through (ghost mode)

### Video Playback

- MPV with libmpv bindings
- Auto hardware acceleration
- PipeWire audio support
- Video loop enabled

### Dependencies

- `ewmh` - Extended Window Manager Hints
- `python-mpv` - MPV/libmpv bindings
- `python-xlib` - X11 protocol bindings
- `six` - Python 2/3 compatibility

## Troubleshooting

### Video not playing
- Check video path in config.json exists
- Verify MP4 format is supported
- Check MPV is installed: `mpv --version`

### No sound
- Check PipeWire/PulseAudio is running
- Verify video has audio track
- Check system volume isn't muted

### Wallpaper not visible
- Ensure wallpapery is running
- Check no other fullscreen windows are covering it
- Verify GPU drivers support hardware acceleration

### High CPU usage
- Disable hardware acceleration: Edit `main.py`, set `hwdec="no"`
- Use a lower resolution video
- Check video codec is H.264 or H.265

## Development

Run diagnostics to check window stacking:

```bash
/home/brandon/Documents/wallpapery/venv/bin/python debug_windows.py
```

Monitor window changes:

```bash
/home/brandon/Documents/wallpapery/venv/bin/python watcher.py
```

## Future Improvements

- [ ] Pause/resume controls
- [ ] Volume control UI
- [ ] Support for multiple videos/slideshow
- [ ] Configurable ignore list for audio muting
- [ ] Desktop shortcut/menu integration
- [ ] Systemd service file for autostart

## License

MIT
