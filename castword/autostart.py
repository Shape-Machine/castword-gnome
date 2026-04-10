"""Manage XDG autostart for castword.

The autostart entry is a .desktop file placed in ~/.config/autostart/.
Its existence is the canonical state — no GSettings key is needed, and
this keeps the setting in sync with GNOME Tweaks automatically.
"""

import shutil
from pathlib import Path

_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_AUTOSTART_FILE = _AUTOSTART_DIR / "xyz.shapemachine.castword-gnome.desktop"


def _desktop_content() -> str:
    exec_path = shutil.which("castword") or "castword"
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=Castword\n"
        "Comment=Rewrite text in any tone with a keypress\n"
        f"Exec={exec_path} --background\n"
        "Icon=xyz.shapemachine.castword-gnome\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Hidden=false\n"
        "NoDisplay=true\n"
    )


def is_autostart_enabled() -> bool:
    """Return True if the autostart desktop file exists."""
    return _AUTOSTART_FILE.exists()


def set_autostart_enabled(enabled: bool) -> None:
    """Create or remove the autostart desktop file."""
    if enabled:
        _AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        _AUTOSTART_FILE.write_text(_desktop_content())
    else:
        _AUTOSTART_FILE.unlink(missing_ok=True)
