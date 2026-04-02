SCHEMA_DIR = data
SCHEMA_FILE = $(SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
SYSTEM_SCHEMA_DIR = /usr/share/glib-2.0/schemas

.PHONY: run install install-schema uninstall-schema compile-schema clean

run: compile-schema
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) castword

compile-schema:
	glib-compile-schemas $(SCHEMA_DIR)

install:
	python3 -m pip install -e .

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
