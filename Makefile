SCHEMA_DIR = data
SCHEMA_FILE = $(SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
SYSTEM_SCHEMA_DIR = /usr/share/glib-2.0/schemas
VENV = .venv
PYTHON = $(VENV)/bin/python3
STAMP = $(VENV)/.installed

# Packaging / install paths
# Override PREFIX=/usr DESTDIR=/staging for package builds
PREFIX  ?= $(HOME)/.local
DESTDIR ?=

DBUS_SERVICE_DIR = $(DESTDIR)$(PREFIX)/share/dbus-1/services
APPLICATIONS_DIR = $(DESTDIR)$(PREFIX)/share/applications
ICONS_SRC_DIR    = data/icons/hicolor
ICONS_DEST_DIR   = $(DESTDIR)$(PREFIX)/share/icons/hicolor
METAINFO_SRC     = data/xyz.shapemachine.castword-gnome.metainfo.xml
METAINFO_DIR     = $(DESTDIR)$(PREFIX)/share/metainfo
SERVICE_SRC      = data/xyz.shapemachine.castword-gnome.service
DESKTOP_SRC      = data/xyz.shapemachine.castword-gnome.desktop

# Release versioning — format: yyyy-mm-dd-NN (e.g. 2026-04-03-00)
VERSION ?=

.PHONY: run install uninstall install-service install-desktop install-icons uninstall-icons \
        install-metainfo uninstall-metainfo install-schema uninstall-schema \
        compile-schema clean release release-deps

run: $(STAMP) compile-schema
	pkill -f '[/]bin/castword$$' 2>/dev/null || true
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) gsettings reset xyz.shapemachine.castword-gnome shortcut-prompted 2>/dev/null || true
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) gsettings reset xyz.shapemachine.castword-gnome tones 2>/dev/null || true
	$(VENV)/bin/python3 -c "from castword.shortcuts import unregister_castword_shortcut; unregister_castword_shortcut()" 2>/dev/null || true
	GSETTINGS_SCHEMA_DIR=$(SCHEMA_DIR) $(VENV)/bin/castword

$(VENV):
	uv venv --python 3.14 --system-site-packages $(VENV)

$(STAMP): $(VENV) pyproject.toml
	uv pip install --python $(PYTHON) -e .
	touch $(STAMP)

install: install-service install-desktop install-schema install-icons install-metainfo
	@echo "castword installed. Set a keyboard shortcut in GNOME Settings → Keyboard → Custom Shortcuts."

uninstall: uninstall-icons uninstall-metainfo uninstall-schema
	rm -f $(DBUS_SERVICE_DIR)/xyz.shapemachine.castword-gnome.service
	rm -f $(APPLICATIONS_DIR)/xyz.shapemachine.castword-gnome.desktop
	@echo "castword uninstalled."

install-service:
ifneq ($(DESTDIR),)
	mkdir -p $(DBUS_SERVICE_DIR)
	sed "s|Exec=.*|Exec=$(PREFIX)/bin/castword|" $(SERVICE_SRC) \
	    > $(DBUS_SERVICE_DIR)/xyz.shapemachine.castword-gnome.service
	@echo "Installed D-Bus service with Exec=$(PREFIX)/bin/castword"
else
	$(MAKE) $(STAMP)
	@CASTWORD_BIN=$$($(VENV)/bin/python3 -c "import shutil; print(shutil.which('castword') or '$(abspath $(VENV))/bin/castword')"); \
	mkdir -p $(DBUS_SERVICE_DIR); \
	sed "s|Exec=.*|Exec=$$CASTWORD_BIN|" $(SERVICE_SRC) > $(DBUS_SERVICE_DIR)/xyz.shapemachine.castword-gnome.service; \
	echo "Installed D-Bus service with Exec=$$CASTWORD_BIN"
endif

install-desktop:
	mkdir -p $(APPLICATIONS_DIR)
	cp $(DESKTOP_SRC) $(APPLICATIONS_DIR)/
ifeq ($(DESTDIR),)
	update-desktop-database $(APPLICATIONS_DIR) 2>/dev/null || true
endif
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
ifeq ($(DESTDIR),)
	gtk-update-icon-cache -f -t $(ICONS_DEST_DIR) 2>/dev/null || true
endif
	@echo "Installed icons."

uninstall-icons:
	rm -f $(ICONS_DEST_DIR)/scalable/apps/xyz.shapemachine.castword-gnome.svg
	@for size in 16x16 22x22 24x24 32x32 48x48 64x64 96x96 128x128 256x256 512x512; do \
		rm -f $(ICONS_DEST_DIR)/$$size/apps/xyz.shapemachine.castword-gnome.png; \
	done
ifeq ($(DESTDIR),)
	gtk-update-icon-cache -f -t $(ICONS_DEST_DIR) 2>/dev/null || true
endif
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

install-schema:
ifneq ($(DESTDIR),)
	mkdir -p $(DESTDIR)$(PREFIX)/share/glib-2.0/schemas
	cp $(SCHEMA_FILE) $(DESTDIR)$(PREFIX)/share/glib-2.0/schemas/
else
	glib-compile-schemas $(SCHEMA_DIR)
	sudo cp $(SCHEMA_FILE) $(SYSTEM_SCHEMA_DIR)/
	sudo glib-compile-schemas $(SYSTEM_SCHEMA_DIR)
endif

uninstall-schema:
	sudo rm -f $(SYSTEM_SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
	sudo glib-compile-schemas $(SYSTEM_SCHEMA_DIR)

clean:
	find . -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -f $(SCHEMA_DIR)/gschemas.compiled
	rm -rf $(VENV)
	rm -rf dist/ _release_staging/ _flatpak_repo/ _flatpak_build/ _appimage/

# ─── Release ──────────────────────────────────────────────────────────────────

# Install all tools needed to run make release.
# Run this once on a new machine before cutting a release.
release-deps:
	sudo pacman -S --needed flatpak-builder github-cli ruby
	sudo gem install fpm
	@mkdir -p $(HOME)/bin
	curl -L -o $(HOME)/bin/appimagetool \
	    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
	chmod +x $(HOME)/bin/appimagetool
	@echo ""
	@echo "Make sure ~/bin is in your PATH (add to ~/.config/fish/config.fish):"
	@echo "  fish_add_path ~/bin"

# Bump version, commit, tag, push, then build and publish all artifacts.
# Usage: make release VERSION=2026-04-03-00
release:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make release VERSION=2026-04-03-00)" && exit 1)
	@echo "==> Bumping version to $(VERSION)"
	sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@TMPFILE=$$(mktemp); \
	printf 'castword-gnome ($(VERSION)-1) unstable; urgency=medium\n\n  * Release $(VERSION).\n\n -- Sri Rang <sri@shapemachine.xyz>  %s\n\n' \
	    "$$(date -R)" > $$TMPFILE; \
	cat packaging/debian/changelog >> $$TMPFILE; \
	mv $$TMPFILE packaging/debian/changelog
	@echo "==> Committing and tagging v$(VERSION)"
	git add pyproject.toml packaging/debian/changelog
	git commit -m "chore: release v$(VERSION)"
	git tag "v$(VERSION)"
	git push origin main "v$(VERSION)"
	@echo "==> Building and publishing"
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION)
