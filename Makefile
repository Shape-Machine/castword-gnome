SCHEMA_DIR = data
SCHEMA_FILE = $(SCHEMA_DIR)/xyz.shapemachine.castword-gnome.gschema.xml
SYSTEM_SCHEMA_DIR = /usr/share/glib-2.0/schemas
VENV = .venv
PYTHON = $(VENV)/bin/python3
STAMP = $(VENV)/.installed

# Packaging / install paths
# Override PREFIX=/usr DESTDIR=/staging for package builds (deb, AUR, Flatpak)
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

.PHONY: run install install-service install-desktop install-icons uninstall-icons \
        install-metainfo uninstall-metainfo install-schema uninstall-schema \
        compile-schema clean tarball deb appimage release gh-release

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
	rm -rf dist/ build/

# ─── Packaging ────────────────────────────────────────────────────────────────

# Source tarball — used by AUR and gh-release
tarball:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make tarball VERSION=2026-04-03-00)" && exit 1)
	mkdir -p dist
	git archive --format=tar.gz \
	    --prefix=castword-gnome-$(VERSION)/ \
	    HEAD \
	    -o dist/castword-gnome-$(VERSION).tar.gz
	@echo "Created dist/castword-gnome-$(VERSION).tar.gz"

# Debian package — requires dpkg-buildpackage (install build-essential devscripts)
deb:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make deb VERSION=2026-04-03-00)" && exit 1)
	mkdir -p dist build/deb
	rm -rf build/deb/castword-gnome-$(VERSION)
	git archive --format=tar HEAD | tar -x -C build/deb
	mv build/deb/$(shell basename $(CURDIR)) build/deb/castword-gnome-$(VERSION) 2>/dev/null || \
	    (mkdir -p build/deb/castword-gnome-$(VERSION) && git archive --format=tar HEAD | tar -x -C build/deb/castword-gnome-$(VERSION))
	cp -r packaging/debian build/deb/castword-gnome-$(VERSION)/debian
	cd build/deb/castword-gnome-$(VERSION) && dpkg-buildpackage -us -uc -b
	cp build/deb/castword-gnome_*.deb dist/ 2>/dev/null || \
	    cp build/deb/*.deb dist/
	@echo "Created .deb in dist/"

# AppImage — requires appimage-builder (pip install appimage-builder)
appimage:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make appimage VERSION=2026-04-03-00)" && exit 1)
	mkdir -p dist
	cd packaging/appimage && VERSION=$(VERSION) appimage-builder --recipe AppImageBuilder.yml
	mv packaging/appimage/Castword-$(VERSION)-x86_64.AppImage dist/ 2>/dev/null || \
	    mv packaging/appimage/Castword-*.AppImage dist/ 2>/dev/null || true
	@echo "Created AppImage in dist/"

# ─── Release ──────────────────────────────────────────────────────────────────

# Bump version, commit, tag, push, and build all distribution artifacts.
# Usage: make release VERSION=2026-04-03-00
release:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make release VERSION=2026-04-03-00)" && exit 1)
	@echo "==> Bumping version to $(VERSION)"
	sed -i 's/^version = ".*"/version = "$(VERSION)"/' pyproject.toml
	@# Prepend a new entry to the Debian changelog
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
	@echo "==> Building distribution artifacts"
	$(MAKE) tarball VERSION=$(VERSION)
	$(MAKE) deb VERSION=$(VERSION)
	$(MAKE) appimage VERSION=$(VERSION)
	@echo "==> Release v$(VERSION) ready. Run: make gh-release VERSION=$(VERSION)"

# Publish a GitHub release and attach dist/ artifacts.
# Usage: make gh-release VERSION=2026-04-03-00
gh-release:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make gh-release VERSION=2026-04-03-00)" && exit 1)
	@test -d dist || (echo "ERROR: dist/ not found — run 'make release VERSION=$(VERSION)' first" && exit 1)
	gh release create "v$(VERSION)" dist/* \
	    --repo Shape-Machine/castword-gnome \
	    --title "v$(VERSION)" \
	    --generate-notes
	@echo "Published: https://github.com/Shape-Machine/castword-gnome/releases/tag/v$(VERSION)"
