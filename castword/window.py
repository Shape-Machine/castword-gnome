import asyncio
import queue
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk, Pango

from castword.audio import AudioRecorder
from castword.diff import word_diff
from castword.tones import tones_from_settings


class CastwordWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Castword")
        self.set_default_size(980, 520)
        self.set_resizable(True)
        self.set_size_request(480, 320)

        self._settings = Gio.Settings(schema_id="xyz.shapemachine.castword-gnome")
        self._migrate_settings()
        self._busy: bool = False
        self._prefs_open: bool = False
        self._transcribing_count: int = 0
        self._recorder = None
        self._provider = None       # cached LLM provider; invalidated on prefs close
        self._stt_provider = None   # cached STT provider; invalidated on STT settings change

        # Persistent event loop for all provider coroutines — avoids per-call
        # loop creation overhead and enables HTTP connection reuse across requests.
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._loop_thread.start()

        # Serialized transcription queue — ensures chunks are appended in speech order
        self._transcribe_queue: queue.Queue = queue.Queue()
        self._transcribe_worker_thread = threading.Thread(
            target=self._transcribe_worker_loop, daemon=True
        )
        self._transcribe_worker_thread.start()

        self.set_hide_on_close(True)

        self._build_ui()
        self._connect_signals()

        self._recorder = AudioRecorder(
            on_chunk=self._on_audio_chunk,
            on_error=self._show_banner,
            on_idle=self._on_mic_idle,
        )
        self.connect("show", self._on_window_shown)
        self.connect("hide", self._on_window_hidden)

        if not self._settings.get_boolean("shortcut-prompted"):
            self._prefs_open = True  # block focus-out dismiss while prompt is pending
            GLib.idle_add(self._prompt_shortcut_setup)

    def _migrate_settings(self) -> None:
        """Reset any settings that reference removed features."""
        from castword.preferences import _STT_PROVIDERS
        if self._settings.get_string("active-stt-provider") not in _STT_PROVIDERS:
            self._settings.reset("active-stt-provider")

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # Toast overlay wraps everything so toasts float above content
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        # ── Toolbar view with header bar ──────────────────────────────
        toolbar_view = Adw.ToolbarView()
        self._toast_overlay.set_child(toolbar_view)

        header_bar = Adw.HeaderBar()
        header_bar.add_css_class("flat")

        menu = Gio.Menu()
        menu.append("Preferences", "app.preferences")
        menu.append("About Castword", "app.about")

        menu_btn = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=menu)
        menu_btn.add_css_class("flat")
        header_bar.pack_end(menu_btn)

        toolbar_view.add_top_bar(header_bar)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(outer)

        # ── Error banner (full width) ─────────────────────────────────
        self._banner = Adw.Banner(title="", revealed=False)
        outer.append(self._banner)

        # ── Mic / status bar (full width, above columns) ──────────────
        self._status_bar = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            visible=False,
            margin_start=12,
            margin_end=12,
            margin_top=8,
        )
        self._status_bar.add_css_class("card")

        self._status_icon_stack = Gtk.Stack()
        self._status_icon_stack.set_margin_start(10)
        self._status_icon_stack.set_margin_top(8)
        self._status_icon_stack.set_margin_bottom(8)
        self._status_icon_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self._recording_status_icon = Gtk.Image()
        self._status_icon_stack.add_named(self._recording_status_icon, "icon")

        self._status_spinner = Gtk.Spinner()
        self._status_icon_stack.add_named(self._status_spinner, "spinner")

        self._recording_status_label = Gtk.Label(hexpand=True, xalign=0.0)
        self._recording_status_label.set_margin_start(2)

        self._recording_toggle_btn = Gtk.Button()
        self._recording_toggle_btn.add_css_class("flat")
        self._recording_toggle_btn.set_can_focus(False)
        self._recording_toggle_btn.set_margin_end(4)
        self._recording_toggle_btn.set_margin_top(4)
        self._recording_toggle_btn.set_margin_bottom(4)
        self._recording_toggle_btn.connect("clicked", self._on_recording_toggle_clicked)

        self._status_bar.append(self._status_icon_stack)
        self._status_bar.append(self._recording_status_label)
        self._status_bar.append(self._recording_toggle_btn)

        self._set_mic_recording(False)  # initialise to paused visual state
        outer.append(self._status_bar)

        # ── Three-column content area ─────────────────────────────────
        columns_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_top=12,
            margin_bottom=12,
            margin_start=12,
            margin_end=12,
            vexpand=True,
        )
        outer.append(columns_box)

        # Column 1: Input (always visible)
        input_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True, vexpand=True)
        input_lbl = Gtk.Label(label="Input", xalign=0.0)
        input_lbl.add_css_class("caption")
        input_lbl.add_css_class("dim-label")
        input_col.append(input_lbl)
        input_scroll = Gtk.ScrolledWindow(
            hexpand=True,
            vexpand=True,
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
        input_col.append(input_scroll)
        columns_box.append(input_col)

        # Sidebar: vertical tone buttons, between input and diff
        self._tone_sidebar = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            valign=Gtk.Align.CENTER,
        )
        sidebar_scroll = Gtk.ScrolledWindow(
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
        )
        sidebar_scroll.set_size_request(150, -1)
        sidebar_scroll.set_child(self._tone_sidebar)
        columns_box.append(sidebar_scroll)

        # Column 2: Diff (hidden pre-rewrite)
        self._diff_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True, vexpand=True, visible=False)
        diff_lbl = Gtk.Label(label="Diff", xalign=0.0)
        diff_lbl.add_css_class("caption")
        diff_lbl.add_css_class("dim-label")
        self._diff_col.append(diff_lbl)
        self._diff_scroll = Gtk.ScrolledWindow(
            hexpand=True,
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
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
        self._diff_col.append(self._diff_scroll)
        columns_box.append(self._diff_col)

        # Column 3: Output — clean rewritten text, read-only (hidden pre-rewrite)
        self._output_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, hexpand=True, vexpand=True, visible=False)
        output_lbl = Gtk.Label(label="Output", xalign=0.0)
        output_lbl.add_css_class("caption")
        output_lbl.add_css_class("dim-label")
        self._output_col.append(output_lbl)
        self._output_scroll = Gtk.ScrolledWindow(
            hexpand=True,
            vexpand=True,
            hscrollbar_policy=Gtk.PolicyType.NEVER,
        )
        self._output_scroll.add_css_class("card")
        self._output_view = Gtk.TextView(
            editable=False,
            cursor_visible=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            top_margin=10,
            bottom_margin=10,
            left_margin=10,
            right_margin=10,
        )
        self._output_buffer = self._output_view.get_buffer()
        self._output_scroll.set_child(self._output_view)
        self._output_col.append(self._output_scroll)
        columns_box.append(self._output_col)

        self._tone_buttons: list[Gtk.Button] = []
        self._rebuild_tone_buttons()

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
            child = self._tone_sidebar.get_first_child()
            if child is None:
                break
            self._tone_sidebar.remove(child)
        self._tone_buttons.clear()

        tones = tones_from_settings(self._settings)
        for tone in tones:
            if not tone.enabled:
                continue
            btn = Gtk.Button()
            btn.add_css_class("pill")
            lbl = Gtk.Label(
                label=tone.name,
            )
            btn.set_child(lbl)
            btn.set_tooltip_text(tone.name)
            btn.connect("clicked", self._on_tone_clicked, tone)
            self._tone_sidebar.append(btn)
            self._tone_buttons.append(btn)

        if not self._tone_buttons:
            placeholder = Gtk.Label(
                label="No tones enabled — add them in Preferences → Tones",
                wrap=True,
                xalign=0.0,
            )
            placeholder.add_css_class("dim-label")
            placeholder.add_css_class("caption")
            self._tone_sidebar.append(placeholder)

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

        # App-level actions so the menu model's "app." prefix resolves correctly
        app = self.get_application()
        prefs_action = Gio.SimpleAction.new("preferences", None)
        prefs_action.connect("activate", self._on_open_preferences)
        app.add_action(prefs_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_open_about)
        app.add_action(about_action)

        # Clear diff when input changes
        self._input_buffer.connect("changed", self._on_input_changed)

        # Stop/start recorder when STT is toggled in preferences
        self._settings.connect("changed::stt-enabled", self._on_stt_enabled_changed)

        # Invalidate STT provider cache when any of its config keys change
        for key in ("active-stt-provider", "whisper-model",
                    "whisper-local-model-path", "whisper-local-binary-path"):
            self._settings.connect(f"changed::{key}", self._on_stt_settings_changed)

    # ------------------------------------------------------------------ #
    # Preferences
    # ------------------------------------------------------------------ #

    def _on_open_preferences(self, *_):
        from castword.preferences import CastwordPreferences
        self._prefs_open = True
        prefs = CastwordPreferences(transient_for=self, modal=False)
        prefs.connect("close-request", self._on_preferences_closed)
        prefs.present()

    def _on_open_about(self, *_):
        from castword.about import show_about
        self._prefs_open = True
        dialog = show_about(self)
        dialog.connect("closed", lambda _: setattr(self, "_prefs_open", False))

    def _on_preferences_closed(self, prefs):
        self._prefs_open = False
        self._invalidate_provider()
        self._rebuild_tone_buttons()
        return False

    def _invalidate_provider(self) -> None:
        """Drop the cached LLM provider. aclose() is deferred to after any in-flight rewrite."""
        self._provider = None

    def _invalidate_stt_provider(self) -> None:
        """Drop the cached STT provider. aclose() is deferred to after any in-flight transcription."""
        self._stt_provider = None

    @staticmethod
    def _close_provider_async(provider, loop: asyncio.AbstractEventLoop) -> None:
        """Schedule aclose() on the event loop and consume any exception."""
        aclose = getattr(provider, "aclose", None)
        if callable(aclose):
            future = asyncio.run_coroutine_threadsafe(aclose(), loop)
            future.add_done_callback(lambda f: f.exception())

    def _on_stt_settings_changed(self, settings, key) -> None:
        """Drop the STT provider cache when any of its config keys change."""
        self._invalidate_stt_provider()

    def _prompt_shortcut_setup(self):
        from castword.shortcuts import find_castword_shortcut
        self._settings.set_boolean("shortcut-prompted", True)
        _, binding = find_castword_shortcut()
        if binding is not None:
            self._prefs_open = False  # no dialog needed, unblock focus-out dismiss
            self._maybe_start_recorder()
            return GLib.SOURCE_REMOVE  # already configured

        self._prefs_open = True
        dialog = Adw.AlertDialog(
            heading="Set up keyboard shortcut?",
            body="Register Super+Shift+W to open castword from anywhere.",
        )
        dialog.add_response("skip", "Not Now")
        dialog.add_response("setup", "Set Up")
        dialog.set_response_appearance("setup", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("setup")
        dialog.connect("response", self._on_shortcut_prompt_response)
        dialog.present(self)
        return GLib.SOURCE_REMOVE

    def _on_shortcut_prompt_response(self, dialog, response):
        self._prefs_open = False
        if response != "setup":
            return
        from castword.shortcuts import find_conflicting_shortcut, format_binding, DEFAULT_BINDING
        conflict_path, conflict_name = find_conflicting_shortcut(DEFAULT_BINDING)
        if conflict_path:
            self._show_shortcut_conflict_dialog(conflict_path, conflict_name, format_binding(DEFAULT_BINDING))
        else:
            self._do_register_shortcut()

    def _show_shortcut_conflict_dialog(self, conflict_path: str, conflict_name: str, binding_label: str):
        self._prefs_open = True
        dialog = Adw.AlertDialog(
            heading="Shortcut already in use",
            body=f'{binding_label} is currently used by \u201c{conflict_name}\u201d. Replace it with castword?',
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("replace", "Replace")
        dialog.set_response_appearance("replace", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_conflict_response, conflict_path)
        dialog.present(self)

    def _on_conflict_response(self, dialog, response, conflict_path: str):
        self._prefs_open = False
        if response != "replace":
            return
        from castword.shortcuts import clear_shortcut_binding
        clear_shortcut_binding(conflict_path)
        self._do_register_shortcut()

    def _do_register_shortcut(self):
        from castword.shortcuts import register_castword_shortcut
        if not register_castword_shortcut():
            self._show_banner("Could not register shortcut — set it up in GNOME Settings → Keyboard.")

    # ------------------------------------------------------------------ #
    # Event handlers
    # ------------------------------------------------------------------ #

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self._dismiss()
            return True
        return False

    def _on_focus_out(self, ctrl):
        if self._settings.get_boolean("dismiss-on-focus-out") and not self._busy and not self._prefs_open:
            self._dismiss()

    def _dismiss(self):
        """Hide the window (keeping the process resident for fast re-activation)."""
        if not self._settings.get_boolean("keep-text-on-dismiss"):
            self._input_buffer.set_text("")
            self._diff_buffer.set_text("")
            self._output_buffer.set_text("")
            self._diff_col.set_visible(False)
            self._output_col.set_visible(False)
            self._hide_banner()
        self.set_visible(False)

    def _on_input_changed(self, buf):
        # Hide diff and output columns when input is cleared
        start, end = buf.get_bounds()
        if not buf.get_text(start, end, False).strip():
            self._diff_col.set_visible(False)
            self._output_col.set_visible(False)
            self._diff_buffer.set_text("")
            self._output_buffer.set_text("")

    def _on_tone_clicked(self, btn, tone):
        start, end = self._input_buffer.get_bounds()
        text = self._input_buffer.get_text(start, end, False).strip()
        if not text:
            return

        # Build the provider on the main thread (GSettings + libsecret must not
        # be called from a background thread), then cache it for subsequent clicks.
        if self._provider is None:
            try:
                from castword.providers import make_provider
                self._provider = make_provider(self._settings)
            except Exception as exc:
                self._show_banner(str(exc))
                return

        self._set_busy(True)
        self._hide_banner()

        threading.Thread(
            target=self._rewrite_thread,
            args=(text, tone, self._provider),
            daemon=True,
        ).start()

    # ------------------------------------------------------------------ #
    # Async rewrite — runs in background thread
    # ------------------------------------------------------------------ #

    def _rewrite_thread(self, text: str, tone, provider):
        try:
            future = asyncio.run_coroutine_threadsafe(
                provider.rewrite(text, tone), self._loop
            )
            result = future.result()
            GLib.idle_add(self._on_rewrite_done, text, result)
        except Exception as exc:
            GLib.idle_add(self._on_rewrite_error, str(exc))
        finally:
            # Close the provider only if it was invalidated while this rewrite was in flight.
            if provider is not self._provider:
                self._close_provider_async(provider, self._loop)

    def _on_rewrite_done(self, original: str, rewritten: str):
        mode = self._settings.get_string("output-mode")

        self._copy_to_clipboard(rewritten)

        if mode == "replace":
            self._input_buffer.set_text(rewritten)
            self._diff_col.set_visible(False)
            self._output_col.set_visible(False)
            self._output_buffer.set_text("")
        elif mode == "clipboard":
            self._diff_col.set_visible(False)
            self._output_col.set_visible(False)
            self._output_buffer.set_text("")
        else:  # clipboard+diff (default)
            self._render_diff(original, rewritten)
            self._output_buffer.set_text(rewritten)
            self._diff_col.set_visible(True)
            self._output_col.set_visible(True)

        self._set_busy(False)
        return GLib.SOURCE_REMOVE

    def _on_rewrite_error(self, message: str):
        self._set_busy(False)
        self._show_banner(message)
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ #
    # STT recording — window show/hide lifecycle
    # ------------------------------------------------------------------ #

    def _on_stt_enabled_changed(self, settings, key) -> None:
        if not settings.get_boolean(key):
            if self._recorder and self._recorder.is_running():
                self._recorder.stop()
                self._set_mic_recording(False)
        self._update_status_bar()

    def _on_window_shown(self, _window) -> None:
        self._maybe_start_recorder()

    def _maybe_start_recorder(self) -> None:
        if (self._settings.get_boolean("stt-enabled")
                and not self._prefs_open
                and not self._recorder.is_running()
                and self.get_visible()):
            self._recorder.start()
            if self._recorder.is_running():
                self._set_mic_recording(True)

    def _on_window_hidden(self, _window) -> None:
        if self._recorder.is_running():
            self._recorder.stop()
            self._set_mic_recording(False)

    def _on_mic_idle(self) -> None:
        self.toggle_mic()
        return GLib.SOURCE_REMOVE

    def toggle_mic(self) -> None:
        """Toggle mic pause/resume. No-op if STT is not enabled."""
        if not self._settings.get_boolean("stt-enabled"):
            return
        if self._recorder.is_running():
            self._recorder.stop()
            self._set_mic_recording(False)
            self._toast_overlay.add_toast(Adw.Toast(title="Mic paused", timeout=2))
        else:
            self._recorder.start()
            if self._recorder.is_running():
                self._set_mic_recording(True)
                self._toast_overlay.add_toast(Adw.Toast(title="Mic recording", timeout=2))

    def _on_recording_toggle_clicked(self, _btn) -> None:
        self.toggle_mic()

    def _set_mic_recording(self, recording: bool) -> None:
        if recording:
            self._recording_status_icon.set_from_icon_name("media-record-symbolic")
            self._recording_status_icon.add_css_class("error")   # red in Adwaita
            self._recording_status_icon.remove_css_class("dim-label")
            self._recording_toggle_btn.set_label("Pause")
        else:
            self._recording_status_icon.set_from_icon_name("audio-input-microphone-symbolic")
            self._recording_status_icon.remove_css_class("error")
            self._recording_status_icon.add_css_class("dim-label")
            self._recording_toggle_btn.set_label("Resume")
        self._update_status_bar()

    def _update_status_bar(self) -> None:
        """Sync the status bar label, icon/spinner, toggle button, and visibility."""
        recording = self._recorder is not None and self._recorder.is_running()
        stt_enabled = self._settings.get_boolean("stt-enabled")

        if self._busy:
            self._recording_status_label.set_text("Rewriting...")
            self._status_icon_stack.set_visible_child_name("spinner")
            self._status_spinner.start()
            self._recording_toggle_btn.set_sensitive(False)
            self._status_bar.set_visible(True)
        elif self._transcribing_count > 0:
            self._recording_status_label.set_text("Transcribing...")
            self._status_icon_stack.set_visible_child_name("spinner")
            self._status_spinner.start()
            self._recording_toggle_btn.set_sensitive(False)
            self._status_bar.set_visible(True)
        elif recording:
            self._recording_status_label.set_text("Listening...")
            self._status_icon_stack.set_visible_child_name("icon")
            self._status_spinner.stop()
            self._recording_toggle_btn.set_sensitive(True)
            self._status_bar.set_visible(True)
        elif stt_enabled:
            self._recording_status_label.set_text("Microphone paused")
            self._status_icon_stack.set_visible_child_name("icon")
            self._status_spinner.stop()
            self._recording_toggle_btn.set_sensitive(True)
            self._status_bar.set_visible(True)
        else:
            self._status_spinner.stop()
            self._status_bar.set_visible(False)

    # ------------------------------------------------------------------ #
    # STT transcription — audio chunk → text
    # ------------------------------------------------------------------ #

    def _on_audio_chunk(self, wav_bytes: bytes) -> None:
        """Called on GTK main thread when AudioRecorder emits a speech chunk."""
        if not self._settings.get_boolean("stt-enabled"):
            return

        # Build the STT provider lazily on the main thread (libsecret must not
        # be called from a background thread), then cache it across chunks.
        if self._stt_provider is None:
            try:
                from castword.providers import make_stt_provider
                self._stt_provider = make_stt_provider(self._settings)
            except Exception as exc:
                self._show_banner(str(exc))
                return

        self._transcribing_count += 1
        self._update_status_bar()
        self._transcribe_queue.put((wav_bytes, self._stt_provider))

    def _transcribe_worker_loop(self) -> None:
        """Single worker thread — processes chunks one at a time to preserve order."""
        while True:
            item = self._transcribe_queue.get()
            if item is None:
                break
            wav_bytes, provider = item
            try:
                future = asyncio.run_coroutine_threadsafe(
                    provider.transcribe(wav_bytes), self._loop
                )
                text = future.result()
                GLib.idle_add(self._on_transcription_done, text.strip() if text else None)
            except Exception as exc:
                GLib.idle_add(self._on_transcription_error, str(exc))
            finally:
                self._transcribe_queue.task_done()
                # Close the provider only if it was invalidated while this chunk was in flight.
                if provider is not self._stt_provider:
                    self._close_provider_async(provider, self._loop)

    def _on_transcription_done(self, text: str | None):
        self._transcribing_count = max(0, self._transcribing_count - 1)
        self._update_status_bar()

        if text:
            buf = self._input_buffer
            existing = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            sep = " " if existing.strip() else ""
            buf.insert(buf.get_end_iter(), sep + text.strip())

            # Auto-copy the full accumulated text
            full_text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            self._copy_to_clipboard(full_text)
        return GLib.SOURCE_REMOVE

    def _on_transcription_error(self, message: str):
        self._transcribing_count = max(0, self._transcribing_count - 1)
        self._update_status_bar()
        self._show_banner(message)
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------------ #
    # Diff rendering
    # ------------------------------------------------------------------ #

    def _render_diff(self, original: str, rewritten: str):
        self._diff_buffer.set_text("")
        tokens = word_diff(original, rewritten)
        for token, tag in tokens:
            insert_pos = self._diff_buffer.get_end_iter()
            if tag == "equal":
                self._diff_buffer.insert(insert_pos, token)
            else:
                self._diff_buffer.insert_with_tags_by_name(insert_pos, token, tag)

    # ------------------------------------------------------------------ #
    # Clipboard
    # ------------------------------------------------------------------ #

    def _copy_to_clipboard(self, text: str):
        from gi.repository import GObject
        display = Gdk.Display.get_default()
        if display is None:
            return
        clipboard = display.get_clipboard()
        val = GObject.Value(GObject.TYPE_STRING, text)
        clipboard.set_content(Gdk.ContentProvider.new_for_value(val))
        toast = Adw.Toast(title="Copied!", timeout=2)
        self._toast_overlay.add_toast(toast)

    # ------------------------------------------------------------------ #
    # Busy state
    # ------------------------------------------------------------------ #

    def _set_busy(self, busy: bool):
        self._busy = busy
        for btn in self._tone_buttons:
            btn.set_sensitive(not busy)
        self._update_status_bar()

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
