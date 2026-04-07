# Features

_Last updated: 2026-04-07_

## Text Rewriting
- Floating overlay window launches instantly from any application via a global keyboard shortcut (Super+Shift+W by default).
- Paste or type text, then click a tone button to rewrite it with AI in one click.
- Result is copied to clipboard automatically with a confirmation toast.
- Word-level diff view highlights exactly what changed — green for additions, red strikethrough for removals.
- Three output modes: clipboard + diff (default), clipboard only, or replace input text in place.

## Tone System
- Seven built-in tones: Direct, Technical, Professional, Social (all enabled by default), plus TL;DR, Flirty, and Playful (disabled by default).
- Create custom tones with a name and a fully editable system prompt.
- Enable, disable, reorder, edit, or delete any tone from Preferences.
- Reset to the built-in defaults at any time.

## AI Providers
- Supports OpenAI (GPT-4o), Anthropic (Claude), Google Gemini, and Ollama (local models).
- Switch providers instantly from Preferences — no restart required.
- API keys are auto-detected from environment variables and shell config files (bash, zsh, fish).
- Keys are stored securely in GNOME Keyring (libsecret), not in plain text.
- Test connection button verifies each provider's setup before use.

## Speech-to-Text
- Microphone recording powered by GStreamer with automatic silence detection.
- Transcribed text is appended to the input buffer and copied to clipboard.
- Two STT providers: OpenAI Whisper (cloud) and local whisper.cpp (fully offline).
- Mic can be paused and resumed without closing the window.

## System Integration
- Runs as a persistent D-Bus service — activates in milliseconds on keypress, stays resident in memory.
- Registered in the GNOME application menu with a custom icon, desktop file, and AppStream metadata.
- Keyboard shortcut setup wizard on first launch with conflict detection and auto-replacement.
- Fully native GNOME look and feel built on GTK4 and Libadwaita.

## Preferences
- Four-page preferences window: Tones, Providers, Behaviour, Speech.
- All changes apply immediately — no save button required.
- Behaviour options include focus-out auto-dismiss and keep/clear text on window close.

## Installation
- Available as AUR package (`yay -S castword-gnome-bin`), `.deb`, `.rpm`, AppImage, Flatpak, and source tarball.
- Single `make install` command for source installs — registers all system files automatically.
