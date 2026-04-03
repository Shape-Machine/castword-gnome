import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gio

# Set prgname to the full app ID so GTK uses it as the Wayland
# xdg_toplevel::app_id, allowing GNOME Shell to match the window to
# xyz.shapemachine.castword-gnome.desktop and display "Castword" in
# Alt+Tab instead of the raw binary name or app ID.
GLib.set_prgname("xyz.shapemachine.castword-gnome")
GLib.set_application_name("Castword")


class CastwordApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="xyz.shapemachine.castword-gnome",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._window = None

    def do_activate(self):
        from castword.window import CastwordWindow

        if self._window is None:
            self._window = CastwordWindow(application=self)
            # Keep the process resident after the window is hidden so
            # D-Bus re-activation can re-present it instantly.
            self.hold()
        self._window.present()


def main():
    app = CastwordApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
