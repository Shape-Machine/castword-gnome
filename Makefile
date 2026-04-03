SCHEMA_DIR = data
SCHEMA_FILE = $(SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
SYSTEM_SCHEMA_DIR = /usr/share/glib-2.0/schemas
VENV = .venv
PYTHON = $(VENV)/bin/python3
STAMP = $(VENV)/.installed

DBUS_SERVICE_DIR = $(HOME)/.local/share/dbus-1/services
APPLICATIONS_DIR = $(HOME)/.local/share/applications
ICONS_SRC_DIR    = data/icons/hicolor
ICONS_DEST_DIR   = $(HOME)/.local/share/icons/hicolor
METAINFO_SRC     = data/xyz.shapemachine.castword-gnome.metainfo.xml
METAINFO_DIR     = $(HOME)/.local/share/metainfo
SERVICE_SRC      = data/xyz.shapemachine.castword-gnome.service
DESKTOP_SRC      = data/xyz.shapemachine.castword-gnome.desktop

.PHONY: run install install-service install-desktop install-icons uninstall-icons install-metainfo uninstall-metainfo install-schema uninstall-schema compile-schema clean

run: $(STAMP) compile-schema
	pkill -f '[b]in/python.*castword\.main' 2>/dev/null || true
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) gsettings reset xyz.shapemachine.castword-gnome shortcut-prompted 2>/dev/null || true
	$(VENV)/bin/python3 -c "from castword.shortcuts import unregister_castword_shortcut; unregister_castword_shortcut()" 2>/dev/null || true
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) $(VENV)/bin/castword

$(VENV):
	uv venv --python 3.14 --system-site-packages $(VENV)

$(STAMP): $(VENV) pyproject.toml
	uv pip install --python $(PYTHON) -e .
	touch $(STAMP)

install: install-service install-desktop install-schema install-icons install-metainfo
	@echo "castword installed. Set a keyboard shortcut in GNOME Settings → Keyboard → Custom Shortcuts."

install-service: $(STAMP)
	@CASTWORD_BIN=$$($(VENV)/bin/python3 -c "import shutil; print(shutil.which('castword') or '$(abspath $(VENV))/bin/castword')"); \
	mkdir -p $(DBUS_SERVICE_DIR); \
	sed "s|Exec=.*|Exec=$$CASTWORD_BIN|" $(SERVICE_SRC) > $(DBUS_SERVICE_DIR)/xyz.shapemachine.castword-gnome.service; \
	echo "Installed D-Bus service with Exec=$$CASTWORD_BIN"

install-desktop:
	mkdir -p $(APPLICATIONS_DIR)
	cp $(DESKTOP_SRC) $(APPLICATIONS_DIR)/
	update-desktop-database $(APPLICATIONS_DIR) 2>/dev/null || true
	@echo "Installed desktop file."

install-icons:
	@for size in 16x16 22x22 24x24 32x32 48x48 64x64 96x96 128x128 256x256 512x512; do \
		mkdir -p $(ICONS_DEST_DIR)/$$size/apps; \
		cp $(ICONS_SRC_DIR)/$$size/apps/xyz.shapemachine.castword-gnome.png \
		   $(ICONS_DEST_DIR)/$$size/apps/; \
	done
	mkdir -p $(ICONS_DEST_DIR)/scalable/apps
	cp $(ICONS_SRC_DIR)/scalable/apps/xyz.shapemachine.castword-gnome.svg \
	   $(ICONS_DEST_DIR)/scalable/apps/
	gtk-update-icon-cache -f -t $(ICONS_DEST_DIR) 2>/dev/null || true
	@echo "Installed icons."

uninstall-icons:
	rm -f $(ICONS_DEST_DIR)/scalable/apps/xyz.shapemachine.castword-gnome.svg
	@for size in 16x16 22x22 24x24 32x32 48x48 64x64 96x96 128x128 256x256 512x512; do \
		rm -f $(ICONS_DEST_DIR)/$$size/apps/xyz.shapemachine.castword-gnome.png; \
	done
	gtk-update-icon-cache -f -t $(ICONS_DEST_DIR) 2>/dev/null || true
	@echo "Uninstalled icons."

install-metainfo:
	mkdir -p $(METAINFO_DIR)
	cp $(METAINFO_SRC) $(METAINFO_DIR)/
	@echo "Installed AppStream metainfo."

uninstall-metainfo:
	rm -f $(METAINFO_DIR)/xyz.shapemachine.castword-gnome.metainfo.xml
	@echo "Uninstalled AppStream metainfo."

compile-schema:
	glib-compile-schemas $(SCHEMA_DIR)

install-schema: compile-schema
	sudo cp $(SCHEMA_FILE) $(SYSTEM_SCHEMA_DIR)/
	sudo glib-compile-schemas $(SYSTEM_SCHEMA_DIR)

uninstall-schema:
	sudo rm -f $(SYSTEM_SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
	sudo glib-compile-schemas $(SYSTEM_SCHEMA_DIR)

clean:
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f $(SCHEMA_DIR)/gschemas.compiled
	rm -rf $(VENV)
