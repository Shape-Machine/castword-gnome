import asyncio
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk

from castword.diff import word_diff
from castword.tones import tones_from_settings


class CastwordWindow(Adw.Window):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("castword")
        self.set_default_size(680, -1)
        self.set_resizable(False)

        self._settings = Gio.Settings(schema_id="xyz.shapemachine.castword-gnome")
        self._rewrite_result: str | None = None

        self._build_ui()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # Toast overlay wraps everything so toasts float above content
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        self._toast_overlay.set_child(outer)

        # ── Error banner ──────────────────────────────────────────────
        self._banner = Adw.Banner(title="", revealed=False)
        outer.append(self._banner)

        # ── Main content area ─────────────────────────────────────────
        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=16,
            margin_bottom=16,
            margin_start=16,
            margin_end=16,
        )
        outer.append(content)

        # ── Input text view ───────────────────────────────────────────
        input_scroll = Gtk.ScrolledWindow(
            min_content_height=120,
            max_content_height=300,
            vexpand=False,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        input_scroll.add_css_class("card")

        self._input_view = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            top_margin=10,
            bottom_margin=10,
            left_margin=10,
            right_margin=10,
            accepts_tab=False,
        )
        self._input_buffer = self._input_view.get_buffer()
        input_scroll.set_child(self._input_view)
        content.append(input_scroll)

        # ── Tone buttons row ──────────────────────────────────────────
        tone_scroll = Gtk.ScrolledWindow(
            vscrollbar_policy=Gtk.PolicyType.NEVER,
            hscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        self._tone_box = Gtk.Box(spacing=8)
        tone_scroll.set_child(self._tone_box)
        content.append(tone_scroll)

        self._tone_buttons: list[Gtk.Button] = []
        self._rebuild_tone_buttons()

        # ── Spinner ───────────────────────────────────────────────────
        self._spinner = Gtk.Spinner(visible=False)
        content.append(self._spinner)

        # ── Diff panel ────────────────────────────────────────────────
        self._diff_scroll = Gtk.ScrolledWindow(
            min_content_height=80,
            max_content_height=300,
            vexpand=False,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            visible=False,
        )
        self._diff_scroll.add_css_class("card")

        self._diff_view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            top_margin=10,
            bottom_margin=10,
            left_margin=10,
            right_margin=10,
        )
        self._diff_buffer = self._diff_view.get_buffer()
        self._setup_diff_tags()
        self._diff_scroll.set_child(self._diff_view)
        content.append(self._diff_scroll)

    def _setup_diff_tags(self):
        tag_table = self._diff_buffer.get_tag_table()

        added_tag = Gtk.TextTag(name="added")
        added_tag.set_property("foreground", "#26a269")  # GNOME green
        tag_table.add(added_tag)

        removed_tag = Gtk.TextTag(name="removed")
        removed_tag.set_property("foreground", "#c01c28")  # GNOME red
        removed_tag.set_property("strikethrough", True)
        tag_table.add(removed_tag)

    def _rebuild_tone_buttons(self):
        # Clear existing buttons
        while True:
            child = self._tone_box.get_first_child()
            if child is None:
                break
            self._tone_box.remove(child)
        self._tone_buttons.clear()

        tones = tones_from_settings(self._settings)
        for tone in tones:
            btn = Gtk.Button(label=tone.name)
            btn.add_css_class("pill")
            btn.set_tooltip_text(tone.system_prompt[:80] + "…")
            btn.connect("clicked", self._on_tone_clicked, tone)
            self._tone_box.append(btn)
            self._tone_buttons.append(btn)

    # ------------------------------------------------------------------ #
    # Signal connections
    # ------------------------------------------------------------------ #

    def _connect_signals(self):
        # Escape to close
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

        # Focus-out dismiss
        focus_ctrl = Gtk.EventControllerFocus()
        focus_ctrl.connect("leave", self._on_focus_out)
        self.add_controller(focus_ctrl)

        # Clear diff when input changes
        self._input_buffer.connect("changed", self._on_input_changed)

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _on_focus_out(self, ctrl):
        if self._settings.get_boolean("dismiss-on-focus-out"):
            self.close()

    def _on_input_changed(self, buf):
        # Hide diff panel when input is cleared
        start, end = buf.get_bounds()
        if not buf.get_text(start, end, False).strip():
            self._diff_scroll.set_visible(False)
            self._diff_buffer.set_text("")
            self._rewrite_result = None

    def _on_tone_clicked(self, btn, tone):
        start, end = self._input_buffer.get_bounds()
        text = self._input_buffer.get_text(start, end, False).strip()
        if not text:
            return

        self._set_busy(True)
        self._hide_banner()

        threading.Thread(
            target=self._rewrite_thread,
            args=(text, tone),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------ #
    # Async rewrite — runs in background thread
    # ------------------------------------------------------------------ #

    def _rewrite_thread(self, text: str, tone):
        try:
            from castword.providers import make_provider
            provider = make_provider(self._settings)
            result = asyncio.run(provider.rewrite(text, tone))
            GLib.idle_add(self._on_rewrite_done, text, result)
        except Exception as exc:
            GLib.idle_add(self._on_rewrite_error, str(exc))

    def _on_rewrite_done(self, original: str, rewritten: str):
        self._rewrite_result = rewritten
        mode = self._settings.get_string("output-mode")

        self._copy_to_clipboard(rewritten)

        if mode == "replace":
            self._input_buffer.set_text(rewritten)
            self._diff_scroll.set_visible(False)
        elif mode == "clipboard":
            self._diff_scroll.set_visible(False)
        else:  # clipboard+diff (default)
            self._render_diff(original, rewritten)
            self._diff_scroll.set_visible(True)

        self._set_busy(False)
        return GLib.SOURCE_REMOVE

    def _on_rewrite_error(self, message: str):
        self._set_busy(False)
        self._show_banner(message)
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ #
    # Diff rendering
    # ------------------------------------------------------------------ #

    def _render_diff(self, original: str, rewritten: str):
        self._diff_buffer.set_text("")
        tokens = word_diff(original, rewritten)
        insert_pos = self._diff_buffer.get_end_iter()
        for token, tag in tokens:
            if tag == "equal":
                self._diff_buffer.insert(insert_pos, token)
            else:
                self._diff_buffer.insert_with_tags_by_name(insert_pos, token, tag)

    # ------------------------------------------------------------------ #
    # Clipboard
    # ------------------------------------------------------------------ #

    def _copy_to_clipboard(self, text: str):
        display = Gdk.Display.get_default()
        if display is None:
            return
        clipboard = display.get_clipboard()
        clipboard.set(text)
        toast = Adw.Toast(title="Copied!", timeout=2)
        self._toast_overlay.add_toast(toast)

    # ------------------------------------------------------------------ #
    # Busy state
    # ------------------------------------------------------------------ #

    def _set_busy(self, busy: bool):
        for btn in self._tone_buttons:
            btn.set_sensitive(not busy)
        self._spinner.set_visible(busy)
        if busy:
            self._spinner.start()
        else:
            self._spinner.stop()

    # ------------------------------------------------------------------ #
    # Error banner
    # ------------------------------------------------------------------ #

    def _show_banner(self, message: str):
        self._banner.set_title(message)
        self._banner.set_revealed(True)
        GLib.timeout_add_seconds(5, self._hide_banner)

    def _hide_banner(self):
        self._banner.set_revealed(False)
        return GLib.SOURCE_REMOVE
