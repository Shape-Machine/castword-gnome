import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio


class CastwordApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="xyz.shapemachine.castword-gnome",
            # IS_SERVICE keeps the process resident after the window is hidden
            # so D-Bus re-activation re-presents the window instantly.
            flags=Gio.ApplicationFlags.IS_SERVICE,
        )
        self._window = None

    def do_activate(self):
        from castword.window import CastwordWindow

        if self._window is None:
            self._window = CastwordWindow(application=self)
        self._window.present()


def main():
    app = CastwordApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
