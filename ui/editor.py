import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from pathlib import Path

class MintpaperEditor(Gtk.Window):
    def __init__(self, app_ref):
        super().__init__(title="Mintpaper Editor")
        self.app_ref = app_ref
        self.set_default_size(450, 450)
        self.set_border_width(15)
        
        # Hide instead of destroy when 'X' is clicked
        self.connect("delete-event", self.on_delete_event)
        
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.add(self.main_box)
        
        # --- 1. Monitor Selector ---
        mon_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        mon_label = Gtk.Label(label="Target Monitor:")
        
        self.mon_combo = Gtk.ComboBoxText()
        for i, engine in enumerate(self.app_ref.engines):
            geo = engine.mon.get('geometry', {})
            self.mon_combo.append_text(f"Monitor {i} ({geo.get('w', 0)}x{geo.get('h', 0)})")
            
        self.mon_combo.set_active(0)
        self.mon_combo.connect("changed", self.on_monitor_changed)
        
        mon_box.pack_start(mon_label, False, False, 0)
        mon_box.pack_start(self.mon_combo, True, True, 0)
        self.main_box.pack_start(mon_box, False, False, 0)
        
        # --- 2. Preset File Picker ---
        preset_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        preset_label = Gtk.Label(label="Active Preset:")
        
        self.preset_chooser = Gtk.FileChooserButton(title="Choose a preset", action=Gtk.FileChooserAction.OPEN)
        self.preset_chooser.connect("file-set", self.on_preset_selected)
        
        preset_box.pack_start(preset_label, False, False, 0)
        preset_box.pack_start(self.preset_chooser, True, True, 0)
        self.main_box.pack_start(preset_box, False, False, 0)

        # Visual divider
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_box.pack_start(separator, False, False, 10)
        
        # --- 3. Dynamic Controls Container ---
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.main_box.pack_start(self.scrolled, True, True, 0)
        
        self.controls_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.scrolled.add(self.controls_box)
        
        self.refresh_ui()

    def on_delete_event(self, widget, event):
        self.hide()
        return True

    def get_selected_monitor_index(self):
        return self.mon_combo.get_active()

    def on_monitor_changed(self, combo):
        self.refresh_ui()

    def on_preset_selected(self, widget):
        file_path = widget.get_filename()
        if not file_path:
            return
            
        mon_idx = self.get_selected_monitor_index()
        # Route the new file to the currently selected monitor via main.py
        self.app_ref.load_preset_to_monitor(mon_idx, file_path)
        self.refresh_ui()

    def refresh_ui(self):
        mon_idx = self.get_selected_monitor_index()
        if mon_idx < 0 or mon_idx >= len(self.app_ref.engines):
            return
            
        engine = self.app_ref.engines[mon_idx]
        plugin = engine.plugin
        
        # Sync the file picker text to match this monitor's current wallpaper
        current_path = engine.mon.get("active_preset_path", "")
        if current_path:
            self.preset_chooser.set_filename(str(Path(current_path).absolute()))
            
        # Clear old dynamically generated widgets
        for child in self.controls_box.get_children():
            self.controls_box.remove(child)
            
        if not plugin:
            return

        # Fetch the settings blueprint from the active plugin
        settings_blueprint = plugin.__class__.get_plugin_settings_info()
        
        # Generate the UI based on the blueprint
        for item in settings_blueprint:
            control_type = item.get('control_type')
            
            if control_type == 'CHECKBOX_AND_SLIDER':
                box = self.build_checkbox_and_slider(item, plugin)
                self.controls_box.pack_start(box, False, False, 0)
                
            elif control_type == 'SLIDER':
                box = self.build_slider(item, plugin)
                self.controls_box.pack_start(box, False, False, 0)
                
            elif control_type == 'FILE_PATH':
                box = self.build_file_picker(item, plugin)
                self.controls_box.pack_start(box, False, False, 0)

        self.controls_box.show_all()

    # --- Dynamic Widget Builders ---

    def build_slider(self, item, plugin):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        label = Gtk.Label(label=item.get('label', 'Setting'))
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)
        
        settings_info = item.get('settings', {})
        lower = settings_info.get('lower', 0)
        upper = settings_info.get('upper', 100)
        prop_name = item.get('property')
        
        current_val = plugin.settings.get(prop_name, lower)
        
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lower, upper, 1)
        scale.set_value(current_val)
        scale.set_draw_value(True)
        
        scale.connect("value-changed", lambda s: self.on_slider_changed(plugin, prop_name, s.get_value()))
        box.pack_start(scale, False, False, 0)
        return box

    def build_checkbox_and_slider(self, item, plugin):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        
        props = item.get('property') 
        defaults = item.get('default') 
        
        muted_prop = props[0]
        vol_prop = props[1]
        
        is_muted = plugin.settings.get(muted_prop, defaults[0])
        volume = plugin.settings.get(vol_prop, defaults[1])
        
        # Checkbox for mute
        cb_settings = item.get('checkbox_settings', {})
        check = Gtk.CheckButton(label=cb_settings.get('label', 'Mute Audio'))
        check.set_active(is_muted)
        check.connect("toggled", lambda c: self.on_mute_toggled(plugin, muted_prop, c.get_active()))
        box.pack_start(check, False, False, 0)
        
        # Slider for volume
        slider_info = item.get('slider_settings', {})
        scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, slider_info.get('lower', 0), slider_info.get('upper', 100), 1)
        scale.set_value(volume)
        scale.set_draw_value(True)
        scale.connect("value-changed", lambda s: self.on_volume_changed(plugin, vol_prop, s.get_value()))
        box.pack_start(scale, False, False, 0)
        
        return box

    def build_file_picker(self, item, plugin):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        label = Gtk.Label(label=item.get('label', 'File'))
        label.set_halign(Gtk.Align.START)
        box.pack_start(label, False, False, 0)
        
        prop_name = item.get('property')
        current_path = plugin.settings.get(prop_name, '')
        
        chooser = Gtk.FileChooserButton(title="Select File", action=Gtk.FileChooserAction.OPEN)
        if current_path:
            chooser.set_filename(str(Path(current_path).absolute()))
            
        chooser.connect("file-set", lambda c: self.on_file_changed(plugin, prop_name, c.get_filename()))
        box.pack_start(chooser, False, False, 0)
        return box

    # --- Event Dispatchers to Plugins ---
    
    def on_slider_changed(self, plugin, prop_name, value):
        plugin.settings[prop_name] = int(value)
        if prop_name == 'fps_limit':
            plugin.engine.handle_event("SET_FPS", {"fps": int(value)})

    def on_mute_toggled(self, plugin, prop_name, is_active):
        plugin.settings[prop_name] = is_active
        plugin.engine.handle_event("SET_MUTED", {"should_mute": is_active})

    def on_volume_changed(self, plugin, prop_name, value):
        plugin.settings[prop_name] = int(value)
        plugin.engine.handle_event("SET_VOLUME", {"volume": int(value)})

    def on_file_changed(self, plugin, prop_name, file_path):
        if file_path:
            plugin.settings[prop_name] = file_path