import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gio

# Set prgname before creating the application so that GTK sets the
# correct Wayland xdg_toplevel::app_id.  Without this, GTK uses the
# binary basename ("castword") and GNOME Shell cannot match the window
# to xyz.shapemachine.castword-gnome.desktop or its icon.
GLib.set_prgname("xyz.shapemachine.castword-gnome")


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
