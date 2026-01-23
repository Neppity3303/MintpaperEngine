import gi
gi.require_version('Gtk', '3.0')
gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, Pango, PangoCairo
import os
import subprocess

class MintpaperControlPanel(Gtk.Window):
    def __init__(self, app_instance):
        super().__init__(title="Mintpaper Control Panel")
        self.app = app_instance
        self.set_border_width(15)
        self.set_default_size(500, 700)
        self.set_resizable(False)

        # Selected Monitor ID (defaults to Primary)
        self.selected_mid = next((m['id'] for m in self.app.config['monitors'] if m['isPrimary']), 0)

        main_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(main_vbox)

        # --- 1. THE MONITOR MAP ---
        main_vbox.pack_start(Gtk.Label(label="<b>Monitor Layout</b> (Click to select)", use_markup=True, xalign=0), False, False, 0)
        
        self.map_area = Gtk.DrawingArea()
        self.map_area.set_size_request(-1, 200)
        self.map_area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.map_area.connect("draw", self.on_draw_map)
        self.map_area.connect("button-press-event", self.on_map_clicked)
        main_vbox.pack_start(self.map_area, False, False, 0)

        main_vbox.pack_start(Gtk.Separator(), False, False, 5)

        # --- 2. SETTINGS AREA ---
        self.settings_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_vbox.pack_start(self.settings_vbox, True, True, 0)
        
        self.refresh_settings_ui()

        # --- 3. APPLY BUTTON ---
        btn_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_layout(Gtk.ButtonBoxStyle.END)
        apply_btn = Gtk.Button(label="Apply Changes")
        apply_btn.connect("clicked", self.on_apply)
        btn_box.add(apply_btn)
        main_vbox.pack_end(btn_box, False, False, 0)

        self.show_all()

        self.connect("delete-event", self.on_hide_window)

    def on_hide_window(self, widget, event):
        self.hide()
        return True

    def get_map_metrics(self, widget):
        """Calculates scaling for drawing and hit-detection."""
        width = widget.get_allocated_width()
        height = widget.get_allocated_height()
        monitors = self.app.config.get('monitors', [])

        if not monitors:
            return 0, 0, 1, 0, 0
        
        try:
            min_x = min(m['geometry']['x'] for m in monitors)
            max_x = max(m['geometry']['x'] + m['geometry']['w'] for m in monitors)
            min_y = min(m['geometry']['y'] for m in monitors)
            max_y = max(m['geometry']['y'] + m['geometry']['h'] for m in monitors)
        except (KeyError, ValueError):
            return 0, 0, 1, 0, 0

        total_w = max_x - min_x
        total_h = max_y - min_y

        padding = 30
        scale = min((width - padding*2) / total_w, (height - padding*2) / total_h)
        off_x = (width - total_w * scale) / 2
        off_y = (height - total_h * scale) / 2

        return min_x, min_y, scale, off_x, off_y

    def refresh_settings_ui(self):
        """Rebuilds UI for the selected monitor."""
        for child in self.settings_vbox.get_children():
            self.settings_vbox.remove(child)

        mon = next((m for m in self.app.config['monitors'] if m['id'] == self.selected_mid), None)
        if not mon: return
        
        title = f"Settings for Monitor {mon['id']}: {mon['name']}"
        if mon['isPrimary']: title += " ★"
        self.settings_vbox.pack_start(Gtk.Label(label=f"<b>{title}</b>", use_markup=True, xalign=0), False, False, 0)

        # --- SOURCE ---
        hbox = Gtk.Box(spacing=6)
        self.source_entry = Gtk.Entry()
        self.source_entry.set_text(mon.get("active_preset_path", ""))
        browse_btn = Gtk.Button(label="Browse")
        browse_btn.connect("clicked", self.on_browse)
        hbox.pack_start(self.source_entry, True, True, 0)
        hbox.pack_start(browse_btn, False, False, 0)
        self.settings_vbox.pack_start(hbox, False, False, 0)

        # --- AUDIO ---
        self.settings_vbox.pack_start(Gtk.Label(label="<b>Audio Settings</b>", use_markup=True, xalign=0), False, False, 0)
        audio_box = Gtk.Box(spacing=10)
        self.mute_check = Gtk.CheckButton(label="Mute")
        self.mute_check.set_active(mon.get("is_muted", False))
        self.mute_check.connect("toggled", self.on_mute_toggled)
        
        self.vol_adj = Gtk.Adjustment(value=mon.get("volume", 50), lower=0, upper=100, step_increment=1)
        self.vol_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.vol_adj)
        self.vol_scale.set_digits(0)
        self.vol_scale.set_sensitive(not self.mute_check.get_active())
        
        audio_box.pack_start(self.mute_check, False, False, 0)
        audio_box.pack_start(self.vol_scale, True, True, 0)
        self.settings_vbox.pack_start(audio_box, False, False, 0)

        # --- PERFORMANCE ---
        self.settings_vbox.pack_start(Gtk.Label(label="<b>Performance</b>", use_markup=True, xalign=0), False, False, 0)
        self.perf_check = Gtk.CheckButton(label="Performance Mode (Auto-Pause when covered)")
        self.perf_check.set_active(mon.get("performance_mode", True))
        self.settings_vbox.pack_start(self.perf_check, False, False, 0)

        fps_hbox = Gtk.Box(spacing=10)
        fps_hbox.pack_start(Gtk.Label(label="FPS Limit:"), False, False, 0)
        self.fps_adj = Gtk.Adjustment(value=mon.get("fps_limit", 60), lower=15, upper=144, step_increment=1)
        self.fps_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.fps_adj)
        self.fps_scale.set_digits(0)
        fps_hbox.pack_start(self.fps_scale, True, True, 0)
        self.settings_vbox.pack_start(fps_hbox, False, False, 0)

        self.show_all()

    def on_draw_map(self, widget, cr):
        if not self.app.engines or len(self.app.engines) == 0:
            return False
        
        if not self.app.engines[0].window.get_realized():
            GLib.timeout_add(200, widget.queue_draw)
            return False
        
        min_x, min_y, scale, off_x, off_y = self.get_map_metrics(widget)
        
        for m in self.app.config['monitors']:
            geo = m['geometry']
            x, y = off_x + (geo['x'] - min_x) * scale, off_y + (geo['y'] - min_y) * scale
            w, h = geo['w'] * scale, geo['h'] * scale

            if m['id'] == self.selected_mid:
                cr.set_source_rgb(0.22, 0.87, 0.76)
                cr.set_line_width(3)
                cr.rectangle(x-3, y-3, w+6, h+6)
                cr.stroke()

            cr.set_source_rgb(0.12, 0.12, 0.12)
            cr.rectangle(x, y, w, h)
            cr.fill_preserve()
            cr.set_source_rgb(0.4, 0.4, 0.4)
            cr.set_line_width(1)
            cr.stroke()

            layout = PangoCairo.create_layout(cr)
            if m['isPrimary']:
                cr.set_source_rgb(1, 0.8, 0)
                layout.set_markup("<span size='large'>★</span>")
                sw, sh = layout.get_pixel_size()
                cr.move_to(x + (w/2) - (sw/2), y + (h/2) - (sh/2))
                PangoCairo.show_layout(cr, layout)

            cr.set_source_rgb(0.7, 0.7, 0.7)
            layout.set_text(f"ID: {m['id']}")
            cr.move_to(x + 5, y + 5)
            PangoCairo.show_layout(cr, layout)

    def on_map_clicked(self, widget, event):
        mx, my, scale, ox, oy = self.get_map_metrics(widget)
        for m in self.app.config['monitors']:
            g = m['geometry']
            x, y = ox + (g['x'] - mx) * scale, oy + (g['y'] - my) * scale
            w, h = g['w'] * scale, g['h'] * scale
            if x <= event.x <= x + w and y <= event.y <= y + h:
                self.selected_mid = m['id']
                self.refresh_settings_ui()
                self.map_area.queue_draw()
                return True
        return True

    def on_mute_toggled(self, widget):
        self.vol_scale.set_sensitive(not widget.get_active())

    def on_apply(self, btn):
        for mon in self.app.config['monitors']:
            if mon['id'] == self.selected_mid:
                mon['active_preset_path'] = self.source_entry.get_text()
                mon['is_muted'] = self.mute_check.get_active()
                mon['volume'] = int(self.vol_adj.get_value())
                mon['performance_mode'] = self.perf_check.get_active()
                mon['fps_limit'] = int(self.fps_adj.get_value())
                break
        self.app.save_config()
        self.app.reload_engines()

    def on_browse(self, btn):
        dialog = Gtk.FileChooserDialog(title="Select Source", parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        if dialog.run() == Gtk.ResponseType.OK:
            self.source_entry.set_text(dialog.get_filename())
        dialog.destroy()

    def on_edit(self, btn):
        path = self.source_entry.get_text()
        if os.path.exists(path):
            subprocess.Popen(["xdg-open", path])