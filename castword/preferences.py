import asyncio
import json
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gio, Gtk

from castword.providers.base import Tone
from castword.tones import default_tones, tones_from_settings


_PROVIDERS = ["openai", "anthropic", "gemini", "ollama"]
_PROVIDER_LABELS = ["OpenAI", "Anthropic", "Google Gemini", "Ollama"]


class CastwordPreferences(Adw.PreferencesWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("castword Preferences")
        self.set_default_size(640, 560)

        self._settings = Gio.Settings(schema_id="xyz.shapemachine.castword-gnome")
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Top-level pages
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.add(self._build_tones_page())
        self.add(self._build_providers_page())
        self.add(self._build_behaviour_page())

    # ================================================================== #
    # Page 1 — Tones
    # ================================================================== #

    def _build_tones_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title="Tones", icon_name="preferences-other-symbolic")

        self._tones_group = Adw.PreferencesGroup(title="Tone Presets")
        page.add(self._tones_group)

        self._tone_rows: list[Gtk.Widget] = []
        self._refresh_tone_rows()

        actions_group = Adw.PreferencesGroup()
        page.add(actions_group)

        add_row = Adw.ButtonRow(title="Add Tone")
        add_row.set_start_icon_name("list-add-symbolic")
        add_row.add_css_class("suggested-action")
        add_row.connect("activated", self._on_add_tone)
        actions_group.add(add_row)

        reset_row = Adw.ButtonRow(title="Reset to Defaults")
        reset_row.set_start_icon_name("edit-undo-symbolic")
        reset_row.connect("activated", self._on_reset_tones)
        actions_group.add(reset_row)

        return page

    def _refresh_tone_rows(self):
        for row in self._tone_rows:
            self._tones_group.remove(row)
        self._tone_rows.clear()

        tones = tones_from_settings(self._settings)
        for i, tone in enumerate(tones):
            row = self._make_tone_row(tone, i, len(tones))
            self._tones_group.add(row)
            self._tone_rows.append(row)

    def _make_tone_row(self, tone: Tone, index: int, total: int) -> Adw.ActionRow:
        row = Adw.ActionRow(title=tone.name, subtitle=tone.system_prompt[:72] + ("…" if len(tone.system_prompt) > 72 else ""))

        # Enable/disable switch
        switch = Gtk.Switch(valign=Gtk.Align.CENTER, active=tone.enabled)
        switch.connect("notify::active", self._on_tone_toggled, index)
        row.add_suffix(switch)

        # Up button
        up_btn = Gtk.Button(icon_name="go-up-symbolic", valign=Gtk.Align.CENTER)
        up_btn.add_css_class("flat")
        up_btn.set_sensitive(index > 0)
        up_btn.connect("clicked", self._on_tone_move, index, -1)
        row.add_suffix(up_btn)

        # Down button
        down_btn = Gtk.Button(icon_name="go-down-symbolic", valign=Gtk.Align.CENTER)
        down_btn.add_css_class("flat")
        down_btn.set_sensitive(index < total - 1)
        down_btn.connect("clicked", self._on_tone_move, index, 1)
        row.add_suffix(down_btn)

        # Edit button
        edit_btn = Gtk.Button(icon_name="document-edit-symbolic", valign=Gtk.Align.CENTER)
        edit_btn.add_css_class("flat")
        edit_btn.connect("clicked", self._on_edit_tone, index)
        row.add_suffix(edit_btn)

        # Delete button
        del_btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER)
        del_btn.add_css_class("flat")
        del_btn.add_css_class("destructive-action")
        del_btn.connect("clicked", self._on_delete_tone, index)
        row.add_suffix(del_btn)

        return row

    def _on_tone_toggled(self, switch, _param, index: int):
        tones = tones_from_settings(self._settings)
        tones[index] = Tone(
            name=tones[index].name,
            system_prompt=tones[index].system_prompt,
            enabled=switch.get_active(),
        )
        self._save_tones(tones)

    def _save_tones(self, tones: list[Tone]):
        data = [{"name": t.name, "system_prompt": t.system_prompt, "enabled": t.enabled} for t in tones]
        self._settings.set_string("tones", json.dumps(data))
        self._refresh_tone_rows()

    def _on_tone_move(self, btn, index: int, direction: int):
        tones = tones_from_settings(self._settings)
        new_index = index + direction
        tones[index], tones[new_index] = tones[new_index], tones[index]
        self._save_tones(tones)

    def _on_delete_tone(self, btn, index: int):
        tones = tones_from_settings(self._settings)
        tones.pop(index)
        self._save_tones(tones)

    def _on_add_tone(self, row):
        self._show_tone_dialog(None, None)

    def _on_edit_tone(self, btn, index: int):
        tones = tones_from_settings(self._settings)
        self._show_tone_dialog(index, tones[index])

    def _on_reset_tones(self, row):
        dialog = Adw.AlertDialog(
            heading="Reset Tones?",
            body="This will replace all tones with the 6 built-in defaults.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reset", "Reset")
        dialog.set_response_appearance("reset", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_reset_confirmed)
        dialog.present(self)

    def _on_reset_confirmed(self, dialog, response):
        if response == "reset":
            self._save_tones(default_tones())

    def _show_tone_dialog(self, index, tone: Tone | None):
        is_edit = tone is not None
        dialog = Adw.AlertDialog(
            heading="Edit Tone" if is_edit else "Add Tone",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_size_request(420, -1)

        name_row = Adw.EntryRow(title="Name")
        if tone:
            name_row.set_text(tone.name)
        box.append(name_row)

        prompt_label = Gtk.Label(label="System Prompt", xalign=0)
        prompt_label.add_css_class("caption")
        box.append(prompt_label)

        prompt_scroll = Gtk.ScrolledWindow(min_content_height=120, max_content_height=200,
                                           hscrollbar_policy=Gtk.PolicyType.NEVER)
        prompt_scroll.add_css_class("card")
        prompt_view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                   top_margin=8, bottom_margin=8,
                                   left_margin=8, right_margin=8)
        if tone:
            prompt_view.get_buffer().set_text(tone.system_prompt)
        prompt_scroll.set_child(prompt_view)
        box.append(prompt_scroll)

        dialog.set_extra_child(box)
        dialog.connect("response", self._on_tone_dialog_response, index, name_row, prompt_view)
        dialog.present(self)

    def _on_tone_dialog_response(self, dialog, response, index, name_row, prompt_view):
        if response != "save":
            return
        name = name_row.get_text().strip()
        buf = prompt_view.get_buffer()
        prompt = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()
        if not name or not prompt:
            return

        tones = tones_from_settings(self._settings)
        existing_enabled = tones[index].enabled if index is not None else True
        new_tone = Tone(name=name, system_prompt=prompt, enabled=existing_enabled)
        if index is None:
            tones.append(new_tone)
        else:
            tones[index] = new_tone
        self._save_tones(tones)

    # ================================================================== #
    # Page 2 — Providers
    # ================================================================== #

    def _build_providers_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title="Providers", icon_name="network-server-symbolic")

        # Provider selector
        selector_group = Adw.PreferencesGroup(title="Active Provider")
        page.add(selector_group)

        self._provider_combo = Adw.ComboRow(title="Provider")
        provider_model = Gtk.StringList.new(_PROVIDER_LABELS)
        self._provider_combo.set_model(provider_model)
        active = self._settings.get_string("active-provider")
        active = active if active in _PROVIDERS else _PROVIDERS[0]
        self._provider_combo.set_selected(_PROVIDERS.index(active))
        self._provider_combo.connect("notify::selected", self._on_provider_changed)
        selector_group.add(self._provider_combo)

        # Per-provider settings — one group per provider, toggled visible/hidden
        self._provider_groups: dict[str, Adw.PreferencesGroup] = {}
        self._key_entries: dict[str, Adw.PasswordEntryRow] = {}
        self._model_entries: dict[str, Adw.EntryRow] = {}

        for provider_id, label in zip(_PROVIDERS, _PROVIDER_LABELS):
            group, key_entry, model_entry = self._build_provider_group(provider_id, label)
            self._provider_groups[provider_id] = group
            if key_entry:
                self._key_entries[provider_id] = key_entry
            if model_entry:
                self._model_entries[provider_id] = model_entry
            page.add(group)

        self._update_provider_visibility(active)
        return page

    def _build_provider_group(self, provider_id: str, label: str):
        group = Adw.PreferencesGroup(title=f"{label} Settings")

        key_entry = None
        model_entry = None

        if provider_id == "ollama":
            url_row = Adw.EntryRow(title="Base URL")
            url_row.set_text(self._settings.get_string("ollama-base-url"))
            url_row.connect("changed", lambda r: self._settings.set_string("ollama-base-url", r.get_text()))
            group.add(url_row)
        else:
            key_entry = Adw.PasswordEntryRow(title="API Key")
            self._prefill_key(provider_id, key_entry)
            # Save on Enter (apply) or focus-out, not on every keystroke
            key_entry.connect("apply", self._on_key_changed, provider_id)
            focus_ctrl = Gtk.EventControllerFocus()
            focus_ctrl.connect("leave", lambda _ctrl, e=key_entry, p=provider_id: self._on_key_changed(e, p))
            key_entry.add_controller(focus_ctrl)
            group.add(key_entry)

        model_key = f"{provider_id}-model"
        model_entry = Adw.EntryRow(title="Model")
        model_entry.set_text(self._settings.get_string(model_key))
        model_entry.connect("changed", lambda r, k=model_key: self._settings.set_string(k, r.get_text()))
        group.add(model_entry)

        # Test connection button
        test_btn = Gtk.Button(label=f"Test {label} Connection")
        test_btn.add_css_class("pill")
        test_btn.set_margin_top(4)
        test_btn.set_margin_bottom(4)
        test_btn.set_halign(Gtk.Align.START)
        test_btn.connect("clicked", self._on_test_connection, provider_id)

        test_row = Adw.ActionRow()
        test_row.add_suffix(test_btn)
        group.add(test_row)

        return group, key_entry, model_entry

    def _prefill_key(self, provider_id: str, entry: Adw.PasswordEntryRow):
        from castword.providers import lookup_secret, store_secret
        from castword import key_scout
        existing = lookup_secret(provider_id)
        if existing:
            entry.set_text(existing)
            return
        discovered = key_scout.scan()
        if provider_id in discovered:
            key = discovered[provider_id]
            entry.set_text(key)
            store_secret(provider_id, key)  # persist to keyring on first discovery

    def _on_key_changed(self, entry, provider_id: str):
        key = entry.get_text().strip()
        if key:
            from castword.providers import store_secret
            store_secret(provider_id, key)

    def _on_provider_changed(self, combo, _param):
        idx = combo.get_selected()
        provider_id = _PROVIDERS[idx]
        self._settings.set_string("active-provider", provider_id)
        self._update_provider_visibility(provider_id)

    def _update_provider_visibility(self, active_provider: str):
        for provider_id, group in self._provider_groups.items():
            group.set_visible(provider_id == active_provider)

    def _on_test_connection(self, btn, provider_id: str):
        from castword.providers import make_provider
        try:
            provider = make_provider(self._settings, provider_id=provider_id)
        except Exception as exc:
            self._on_test_done(btn, False, str(exc))
            return
        btn.set_sensitive(False)
        threading.Thread(
            target=self._test_thread,
            args=(btn, provider),
            daemon=True,
        ).start()

    def _test_thread(self, btn, provider):
        try:
            test_tone = Tone(
                name="test",
                system_prompt="Return only the word OK, nothing else.",
            )

            async def _run():
                try:
                    return await provider.rewrite("test", test_tone)
                finally:
                    aclose = getattr(provider, "aclose", None)
                    if callable(aclose):
                        await aclose()

            asyncio.run(_run())
            GLib.idle_add(self._on_test_done, btn, True, "Connection successful")
        except Exception as exc:
            GLib.idle_add(self._on_test_done, btn, False, str(exc))

    def _on_test_done(self, btn, success: bool, message: str):
        btn.set_sensitive(True)
        toast = Adw.Toast(
            title=("✓ " if success else "✗ ") + message,
            timeout=4,
        )
        self.add_toast(toast)
        return GLib.SOURCE_REMOVE

    # ================================================================== #
    # Page 3 — Behaviour
    # ================================================================== #

    def _build_behaviour_page(self) -> Adw.PreferencesPage:
        page = Adw.PreferencesPage(title="Behaviour", icon_name="preferences-system-symbolic")

        output_group = Adw.PreferencesGroup(title="Output")
        page.add(output_group)

        output_combo = Adw.ComboRow(title="Output Mode")
        output_model = Gtk.StringList.new(["Clipboard + Diff", "Clipboard Only", "Replace Input"])
        output_combo.set_model(output_model)
        mode_map = {"clipboard+diff": 0, "clipboard": 1, "replace": 2}
        current_mode = self._settings.get_string("output-mode")
        output_combo.set_selected(mode_map.get(current_mode, 0))
        output_combo.connect("notify::selected", self._on_output_mode_changed)
        output_group.add(output_combo)

        dismiss_group = Adw.PreferencesGroup(title="Window")
        page.add(dismiss_group)

        dismiss_row = Adw.SwitchRow(title="Dismiss on Focus Loss",
                                    subtitle="Close the overlay when clicking outside it")
        self._settings.bind("dismiss-on-focus-out", dismiss_row, "active",
                            Gio.SettingsBindFlags.DEFAULT)
        dismiss_group.add(dismiss_row)

        shortcut_group = Adw.PreferencesGroup(title="Keyboard Shortcut")
        page.add(shortcut_group)

        from castword.shortcuts import find_castword_shortcut, format_binding
        _, binding = find_castword_shortcut()
        shortcut_row = Adw.ActionRow(
            title="Global Shortcut",
            subtitle=format_binding(binding),
        )
        open_kb_btn = Gtk.Button(label="Open Keyboard Settings", valign=Gtk.Align.CENTER)
        open_kb_btn.add_css_class("flat")
        open_kb_btn.connect("clicked", self._on_open_keyboard_settings)
        shortcut_row.add_suffix(open_kb_btn)
        shortcut_group.add(shortcut_row)

        # STT placeholder (Phase 2)
        stt_group = Adw.PreferencesGroup(title="Voice Input (Phase 2)")
        page.add(stt_group)

        stt_row = Adw.ActionRow(
            title="Speech-to-Text Provider",
            subtitle="Coming in Phase 2",
            sensitive=False,
        )
        stt_row.add_suffix(Gtk.Image(icon_name="audio-input-microphone-symbolic",
                                     valign=Gtk.Align.CENTER))
        stt_group.add(stt_row)

        return page

    def _on_output_mode_changed(self, combo, _param):
        modes = ["clipboard+diff", "clipboard", "replace"]
        self._settings.set_string("output-mode", modes[combo.get_selected()])

    def _on_open_keyboard_settings(self, btn):
        import subprocess
        try:
            subprocess.Popen(["gnome-control-center", "keyboard"], start_new_session=True)
        except FileNotFoundError:
            pass
