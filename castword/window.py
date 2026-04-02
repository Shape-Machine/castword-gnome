import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class CastwordWindow(Adw.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("castword")
        self.set_default_size(680, -1)
        self.set_resizable(False)

        # Placeholder content — replaced in Epic 3
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=24, margin_bottom=24, margin_start=24, margin_end=24)
        box.append(Gtk.Label(label="castword — coming soon"))
        self.set_content(box)

        # Escape dismisses
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == 65307:  # GDK_KEY_Escape
            self.close()
            return True
        return False
