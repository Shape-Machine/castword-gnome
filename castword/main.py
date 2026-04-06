import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw


class CastwordApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="xyz.shapemachine.castword-gnome")
        self.connect("activate", self._on_activate)
        self.set_resource_base_path("/xyz/shapemachine/castword-gnome")
        self._window = None

    def _on_activate(self, app):
        from castword.window import CastwordWindow

        if self._window is None:
            self._window = CastwordWindow(application=self)
            # Keep the process resident after the window is hidden so
            # D-Bus re-activation can re-present it instantly.
            self.hold()

        if self._window.get_visible():
            self._window.toggle_mic()
        else:
            self._window.present()


def main():
    app = CastwordApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
