"""
Helpers for detecting and registering the castword GNOME keyboard shortcut.
All functions fail silently if the GNOME settings-daemon schema is absent
(e.g. non-GNOME desktops).
"""

from gi.repository import Gio

_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys"
_BINDING_SCHEMA = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
_BASE_PATH = "/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"
_COMMAND = "gio launch xyz.shapemachine.castword-gnome"
_DEFAULT_BINDING = "<Super><Shift>c"
_SHORTCUT_NAME = "castword"


def find_castword_shortcut() -> tuple[str | None, str | None]:
    """Return (slot_path, binding) of the existing castword shortcut, or (None, None)."""
    try:
        media_keys = Gio.Settings.new(_SCHEMA)
        slots = media_keys.get_strv("custom-keybindings")
    except Exception:
        return None, None

    for slot in slots:
        try:
            s = Gio.Settings.new_with_path(_BINDING_SCHEMA, slot)
            if "castword" in s.get_string("command"):
                return slot, s.get_string("binding")
        except Exception:
            continue

    return None, None


def register_castword_shortcut(binding: str = _DEFAULT_BINDING) -> bool:
    """Register (or update) the castword shortcut. Returns True on success."""
    try:
        media_keys = Gio.Settings.new(_SCHEMA)
        existing = media_keys.get_strv("custom-keybindings")

        # Reuse existing castword slot or find a free one
        target_path = None
        for slot in existing:
            try:
                s = Gio.Settings.new_with_path(_BINDING_SCHEMA, slot)
                if "castword" in s.get_string("command"):
                    target_path = slot
                    break
            except Exception:
                continue

        if target_path is None:
            idx = 0
            while True:
                candidate = f"{_BASE_PATH}custom{idx}/"
                if candidate not in existing:
                    target_path = candidate
                    break
                idx += 1

        s = Gio.Settings.new_with_path(_BINDING_SCHEMA, target_path)
        s.set_string("name", _SHORTCUT_NAME)
        s.set_string("command", _COMMAND)
        s.set_string("binding", binding)

        if target_path not in existing:
            media_keys.set_strv("custom-keybindings", existing + [target_path])

        return True
    except Exception:
        return False


def unregister_castword_shortcut() -> bool:
    """Remove the castword shortcut entry. Returns True on success."""
    try:
        media_keys = Gio.Settings.new(_SCHEMA)
        existing = media_keys.get_strv("custom-keybindings")
        to_remove = []
        for slot in existing:
            try:
                s = Gio.Settings.new_with_path(_BINDING_SCHEMA, slot)
                if "castword" in s.get_string("command"):
                    to_remove.append(slot)
            except Exception:
                continue
        if not to_remove:
            return True
        media_keys.set_strv("custom-keybindings", [s for s in existing if s not in to_remove])
        return True
    except Exception:
        return False


def format_binding(binding: str | None) -> str:
    """Return a human-readable label for a GSettings binding string."""
    if not binding:
        return "Not set"
    return (
        binding
        .replace("<Super>", "Super+")
        .replace("<Shift>", "Shift+")
        .replace("<Control>", "Ctrl+")
        .replace("<Alt>", "Alt+")
        .replace("<Primary>", "Ctrl+")
    )
