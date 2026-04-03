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

    def do_activate(self):
        from castword.window import CastwordWindow

        win = self.get_active_window()
        if win is None:
            win = CastwordWindow(application=self)
        win.present()


def main():
    app = CastwordApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
