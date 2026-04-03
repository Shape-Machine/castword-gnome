import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio


class CastwordApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="xyz.shapemachine.castword-gnome",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self._window = None

    def do_startup(self):
        super().do_startup()
        # Hold a reference so the process stays resident after the window is
        # hidden — D-Bus re-activation will call do_activate() again.
        self.hold()

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
