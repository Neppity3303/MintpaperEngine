import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
import subprocess
import os

class MintpaperControlPanel(Gtk.Window):
    def __init__(self, app_instance):
        super().__init__(title="Mintpaper Control Panel")
        self.app = app_instance
        self.set_border_width(10)
        self.set_default_size(400, 300)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(vbox)

        # --- Monitor 0 Section ---
        vbox.pack_start(Gtk.Label(label="<b>Primary Monitor (0)</b>", use_markup=True), False, False, 0)
        self.mon0_entry = self._create_source_row(vbox, "primary_source")

        vbox.pack_start(Gtk.Separator(), False, False, 5)

        # --- Monitor 1 Section ---
        vbox.pack_start(Gtk.Label(label="<b>Secondary Monitor (1)</b>", use_markup=True), False, False, 0)
        self.mon1_entry = self._create_source_row(vbox, "secondary_source")

        # --- Control Buttons ---
        btn_box = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        btn_box.set_layout(Gtk.ButtonBoxStyle.END)
        
        apply_btn = Gtk.Button(label="Apply Changes")
        apply_btn.connect("clicked", self.on_apply)
        btn_box.add(apply_btn)
        
        vbox.pack_end(btn_box, False, False, 0)
        self.show_all()

    def _create_source_row(self, container, config_key):
        hbox = Gtk.Box(spacing=6)
        entry = Gtk.Entry()
        entry.set_text(self.app.config.get(config_key, ""))
        
        browse_btn = Gtk.Button(label="Browse")
        browse_btn.connect("clicked", self.on_browse, entry)
        
        edit_btn = Gtk.Button(label="Edit HTML")
        edit_btn.connect("clicked", self.on_edit, entry)

        hbox.pack_start(entry, True, True, 0)
        hbox.pack_start(browse_btn, False, False, 0)
        hbox.pack_start(edit_btn, False, False, 0)
        container.pack_start(hbox, False, False, 0)
        return entry

    def on_browse(self, btn, entry):
        dialog = Gtk.FileChooserDialog(
            title="Select Source File", parent=self,
            action=Gtk.FileChooserAction.OPEN
        )
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        
        filter_any = Gtk.FileFilter()
        filter_any.set_name("Wallpapery Sources")
        filter_any.add_pattern("*.mp4")
        filter_any.add_pattern("*.html")
        dialog.add_filter(filter_any)

        if dialog.run() == Gtk.ResponseType.OK:
            entry.set_text(dialog.get_filename())
        dialog.destroy()

    def on_edit(self, btn, entry):
        path = entry.get_text()
        if path.endswith(".html") and os.path.exists(path):
            # Opens the file in Mint's default editor (Xed, VS Code, etc)
            try:
                subprocess.Popen(["xed", path])
            except FileNotFoundError:
                subprocess.Popen(["xdg-open", path])

    def on_apply(self, btn):
        self.app.config["primary_source"] = self.mon0_entry.get_text()
        self.app.config["secondary_source"] = self.mon1_entry.get_text()
        self.app.save_config()
        self.app.reload_engines()