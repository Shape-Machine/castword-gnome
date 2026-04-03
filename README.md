<p align="center">
  <img src="data/icons/hicolor/scalable/apps/xyz.shapemachine.castword-gnome.svg" width="400" alt="castword icon" />
</p>

# castword

A GNOME quick-launcher overlay that rewrites your draft text in any tone — formal, concise, playful, executive, and more — via a single keypress.

---

## What is castword?

castword sits silently in the background as a D-Bus service. When you press your configured shortcut, it opens a floating overlay where you can paste or type text, choose a rewrite tone, and get the result copied straight to your clipboard — without leaving whatever you were doing.

**Key features:**
- Instant overlay — no window switching
- Multiple rewrite tones (Formal, Concise, Executive, Direct, and more)
- Supports OpenAI, Anthropic, Gemini, and Ollama (local)
- API keys auto-detected from your shell environment
- Fully customisable tones via the Preferences window
- GNOME-native: GTK4 + Libadwaita, D-Bus activated

---

## Install

### Quick install (recommended)

**Prerequisites:** Python 3.11+, GTK4, Libadwaita, `uv`

On Arch: `sudo pacman -S python-gobject`  
On Debian/Ubuntu: `sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1`

```bash
git clone https://github.com/Shape-Machine/castword-gnome.git
cd castword-gnome
make install
```

`make install` does everything in one shot: creates a `.venv`, installs the package, registers the D-Bus service, installs the desktop file, icons, AppStream metadata, and the GSettings schema.

### Packages _(coming soon)_

| Format | Status |
|---|---|
| Arch AUR (`castword-gnome`) | planned |
| Debian `.deb` | planned |
| Flatpak | planned |
| AppImage | planned |

---

## Register the D-Bus service

`make install` handles this automatically. The D-Bus service file is written to `~/.local/share/dbus-1/services/` so that GNOME can activate castword on demand — you do not need to keep it running in the background yourself.

If you ever need to re-register manually:

```bash
make install-service
```

To verify activation is working:

```bash
gdbus call --session \
  --dest xyz.shapemachine.castword-gnome \
  --object-path /xyz/shapemachine/castword_gnome \
  --method xyz.shapemachine.castword_gnome.Activate
```

---

## Set up a keyboard shortcut

castword is launched via a custom GNOME keyboard shortcut. After running `make install`:

1. Open **GNOME Settings → Keyboard → Keyboard Shortcuts → View and Customise Shortcuts → Custom Shortcuts**
2. Click **+** to add a new shortcut
3. Set:
   - **Name:** `castword`
   - **Command:** path printed by `which castword` (e.g. `/home/you/.venv/bin/castword` or `/home/you/castword-gnome/.venv/bin/castword`)
   - **Shortcut:** your preferred key combo (e.g. `Super+W`)

The app will prompt you to set a shortcut on first launch if none is configured.

---

## Configure a provider

castword auto-detects API keys from your environment — no manual config step is needed if your keys are already exported in `~/.bashrc`, `~/.zshrc`, `~/.profile`, `~/.config/fish/config.fish`, or `~/.env`.

| Provider | Environment variable |
|---|---|
| OpenAI | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| Ollama | _(no key needed — runs locally)_ |

If you prefer to keep the key separate, create `~/.config/castword/.env`:

```bash
mkdir -p ~/.config/castword
echo 'OPENAI_API_KEY=sk-...' >> ~/.config/castword/.env
```

### Switching provider and model

Open **castword → Preferences (gear icon) → Provider** and choose the provider and model from the dropdowns. Changes take effect immediately.

### Ollama (local)

Start Ollama with your chosen model before launching castword:

```bash
ollama serve
ollama pull llama3
```

Then select **Ollama** in Preferences and pick the model.

---

## Customise tones

Tones are rewrite instructions sent to the LLM alongside your text. castword ships with six defaults:

| Tone | Enabled by default |
|---|---|
| Formal | yes |
| Concise | yes |
| Executive | yes |
| Direct | yes |
| Playful | no |
| Friendly | no |

To add, edit, reorder, or toggle tones: open **Preferences → Tones**. Each tone has a name and a system prompt — the system prompt is the instruction that shapes how the LLM rewrites your text.

---

## Contributing

Bug reports and feature requests: [github.com/Shape-Machine/castword-gnome/issues](https://github.com/Shape-Machine/castword-gnome/issues)

### Development

```bash
git clone https://github.com/Shape-Machine/castword-gnome.git
cd castword-gnome
make run    # compiles schema locally and launches the app
```

Useful make targets:

| Command | Description |
|---|---|
| `make run` | Compile schema locally and launch |
| `make install` | Full install (venv + service + desktop + schema + icons) |
| `make install-schema` | Copy GSettings schema system-wide (needed for D-Bus activation) |
| `make uninstall-schema` | Remove system-wide schema |
| `make compile-schema` | Recompile schema in `data/` only |
| `make clean` | Remove `__pycache__`, `.pyc`, compiled schema, and `.venv` |
