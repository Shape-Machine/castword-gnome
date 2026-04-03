---
name: castword-gnome-make-run
description: Clean build and run the castword-gnome app (make clean run)
---

Run `make clean run` in the castword-gnome project root directory (`/home/sri/Work/Castword/castword-gnome`).

Use the Bash tool to execute:
```
cd /home/sri/Work/Castword/castword-gnome && make clean && make run
```

This will:
1. Clean all `__pycache__`, `.pyc` files, `gschemas.compiled`, and the `.venv`
2. Recreate the venv, install deps, compile the GSettings schema, and launch the app
