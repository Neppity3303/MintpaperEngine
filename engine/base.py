class MintpaperEvents:
    SET_MUTED = "SET_MUTED"
    SET_PAUSED = "SET_PAUSED"
    # Future events like MOUSE_MOVE can go here

class MintpaperPlugin:
    def __init__(self, engine, settings):
        self.engine = engine      # The MintpaperEngine (the GTK window)
        self.settings = settings  # The dictionary from config.json
        self.is_ready = False

    def setup(self):
        """Called when the plugin is first loaded. Must return True if successful."""
        raise NotImplementedError("Plugins must implement setup()")

    def teardown(self):
        """Called when the plugin is being destroyed or swapped."""
        pass

    def handle_event(self, event_type, data):
        """The main pipeline for all state changes (pause, mute, etc)."""
        pass