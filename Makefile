SCHEMA_DIR = data
SCHEMA_FILE = $(SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
SYSTEM_SCHEMA_DIR = /usr/share/glib-2.0/schemas
VENV = .venv
PYTHON = $(VENV)/bin/python3
STAMP = $(VENV)/.installed

DBUS_SERVICE_DIR = $(HOME)/.local/share/dbus-1/services
APPLICATIONS_DIR = $(HOME)/.local/share/applications
SERVICE_SRC = data/xyz.shapemachine.castword-gnome.service
DESKTOP_SRC = data/xyz.shapemachine.castword-gnome.desktop

.PHONY: run install install-service install-desktop install-schema uninstall-schema compile-schema clean

run: $(STAMP) compile-schema
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) gsettings reset xyz.shapemachine.castword-gnome shortcut-prompted 2>/dev/null || true
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) $(VENV)/bin/castword

$(VENV):
	uv venv --python 3.14 --system-site-packages $(VENV)

$(STAMP): $(VENV) pyproject.toml
	uv pip install --python $(PYTHON) -e .
	touch $(STAMP)

install: install-service install-desktop install-schema
	@echo "castword installed. Run 'scripts/setup-shortcut.sh' to register the keyboard shortcut."

install-service: $(STAMP)
	@CASTWORD_BIN=$$($(VENV)/bin/python3 -c "import shutil; print(shutil.which('castword') or '$(VENV)/bin/castword')"); \
	mkdir -p $(DBUS_SERVICE_DIR); \
	sed "s|Exec=.*|Exec=$$CASTWORD_BIN|" $(SERVICE_SRC) > $(DBUS_SERVICE_DIR)/xyz.shapemachine.castword-gnome.service; \
	echo "Installed D-Bus service with Exec=$$CASTWORD_BIN"

install-desktop:
	mkdir -p $(APPLICATIONS_DIR)
	cp $(DESKTOP_SRC) $(APPLICATIONS_DIR)/
	update-desktop-database $(APPLICATIONS_DIR) 2>/dev/null || true
	@echo "Installed desktop file."

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
