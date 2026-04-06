import importlib.metadata

import gi

gi.require_version("Adw", "1")
gi.require_version("Gtk", "4.0")
from gi.repository import Adw, Gtk


def show_about(parent) -> None:
    try:
        version = importlib.metadata.version("castword-gnome")
    except importlib.metadata.PackageNotFoundError:
        version = "dev"

    dialog = Adw.AboutDialog(
        application_name="Castword",
        application_icon="xyz.shapemachine.castword-gnome",
        version=version,
        developer_name="Sri Rang",
        website="https://shapemachine.xyz/castword",
        issue_url="https://github.com/Shape-Machine/castword-gnome/issues",
        license_type=Gtk.License.MIT_X11,
        copyright="© 2026 Sri Rang",
        developers=["Sri Rang"],
    )
    dialog.present(parent)
