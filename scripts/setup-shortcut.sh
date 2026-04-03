#!/usr/bin/env bash
# setup-shortcut.sh — Register a GNOME custom keyboard shortcut for castword.
#
# Default binding: Super+Shift+C
# The shortcut runs: gio launch xyz.shapemachine.castword-gnome
# which honours DBusActivatable=true — it re-presents a running instance
# rather than launching a second process.
#
# Usage:
#   scripts/setup-shortcut.sh              # uses Super+Shift+C
#   BINDING="<Alt>space" scripts/setup-shortcut.sh
#
# Idempotent: running the script twice will not create duplicate entries.

set -euo pipefail

BINDING="${BINDING:-<Super>space}"
SHORTCUT_NAME="castword"

# Resolve the castword binary — full path required because D-Bus activation
# runs in a minimal environment without the user's PATH.
CASTWORD_BIN=$(command -v castword 2>/dev/null || true)
if [[ -z "$CASTWORD_BIN" ]]; then
    echo "Error: castword not found on PATH. Run 'make install' first." >&2
    exit 1
fi
COMMAND="$CASTWORD_BIN"

SCHEMA="org.gnome.settings-daemon.plugins.media-keys"
KEY="custom-keybindings"
BASE_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings"

# ── Find an unused slot or an existing castword entry ────────────────────────
existing_slots=$(gsettings get "$SCHEMA" "$KEY" | tr -d "[]' " | tr ',' '\n' | grep -v '^$' || true)

target_path=""
for slot in $existing_slots; do
    slot_name=$(gsettings get org.gnome.settings-daemon.plugins.media-keys.custom-keybinding:/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/"$slot"/ name 2>/dev/null | tr -d "'" || true)
    if [[ "$slot_name" == "$SHORTCUT_NAME" ]]; then
        target_path="${BASE_PATH}/${slot}/"
        echo "Found existing castword shortcut at ${target_path} — updating."
        break
    fi
done

if [[ -z "$target_path" ]]; then
    # Find the next available custom0, custom1, … slot
    idx=0
    while true; do
        candidate="${BASE_PATH}/custom${idx}/"
        if ! echo "$existing_slots" | grep -qx "custom${idx}"; then
            target_path="$candidate"
            break
        fi
        (( idx++ ))
    done
    echo "Registering new shortcut at ${target_path}"
fi

slot_id=$(basename "${target_path%/}")

# ── Write the shortcut properties ────────────────────────────────────────────
BINDING_SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
gsettings set "${BINDING_SCHEMA}:${target_path}" name    "'${SHORTCUT_NAME}'"
gsettings set "${BINDING_SCHEMA}:${target_path}" command "'${COMMAND}'"
gsettings set "${BINDING_SCHEMA}:${target_path}" binding "'${BINDING}'"

# ── Add slot to the list (idempotent) ─────────────────────────────────────────
current_list=$(gsettings get "$SCHEMA" "$KEY")
if echo "$current_list" | grep -q "$slot_id"; then
    : # already in list
else
    if [[ "$current_list" == "@as []" || "$current_list" == "[]" ]]; then
        new_list="['${target_path}']"
    else
        new_list="${current_list%]}, '${target_path}']"
    fi
    gsettings set "$SCHEMA" "$KEY" "$new_list"
fi

echo ""
echo "Done. Shortcut registered:"
echo "  Name:    ${SHORTCUT_NAME}"
echo "  Binding: ${BINDING}"
echo "  Command: ${COMMAND}"
echo ""
echo "Press ${BINDING} to open castword."
echo "(Make sure 'make install-service' has been run first.)"
