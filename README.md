# castword

A GNOME quick-launcher overlay that rewrites your draft text in any tone — formal, concise, playful, executive, and more — via a single keypress.

## Developers

**Prerequisites:** Python 3.11+, GTK4, Libadwaita (`python-gobject` on Arch / `python3-gi` on Debian).

```bash
# 1. Install the package in editable mode
make install

# 2. Install the GSettings schema system-wide (once)
make install-schema

# 3. Run
make run
```

| Command | Description |
|---|---|
| `make run` | Compile schema locally and launch the app |
| `make install` | Install package in editable mode (`pip install -e .`) |
| `make install-schema` | Copy schema system-wide and recompile (required for D-Bus activation) |
| `make uninstall-schema` | Remove system-wide schema |
| `make compile-schema` | Recompile schema in `data/` only |
| `make clean` | Remove `__pycache__`, `.pyc`, and compiled schema |
