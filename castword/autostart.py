"""Manage XDG autostart for castword.

The autostart entry is a .desktop file placed in ~/.config/autostart/.
Its existence is the canonical state — no GSettings key is needed, and
this keeps the setting in sync with GNOME Tweaks automatically.
"""

from pathlib import Path

_AUTOSTART_DIR = Path.home() / ".config" / "autostart"
_AUTOSTART_FILE = _AUTOSTART_DIR / "xyz.shapemachine.castword-gnome.desktop"

_DESKTOP_CONTENT = """\
[Desktop Entry]
Type=Application
Name=Castword
Comment=Rewrite text in any tone with a keypress
Exec=castword --background
Icon=xyz.shapemachine.castword-gnome
X-GNOME-Autostart-enabled=true
Hidden=false
NoDisplay=true
"""


def is_autostart_enabled() -> bool:
    """Return True if the autostart desktop file exists."""
    return _AUTOSTART_FILE.exists()


def set_autostart_enabled(enabled: bool) -> None:
    """Create or remove the autostart desktop file."""
    if enabled:
        _AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        _AUTOSTART_FILE.write_text(_DESKTOP_CONTENT)
    else:
        _AUTOSTART_FILE.unlink(missing_ok=True)
