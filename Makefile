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
        compile-schema clean release release-deps \
        tarball deb rpm appimage flatpak gh-release

run: $(STAMP) compile-schema
	pkill -f 'castword[.]main' 2>/dev/null || true
	pkill -f '[/]bin/castword$$' 2>/dev/null || true
	sleep 0.3
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
	@# Also clean up any system-wide leftovers from a previous PREFIX=/usr install
	@sudo rm -f /usr/share/icons/hicolor/scalable/apps/xyz.shapemachine.castword-gnome.svg 2>/dev/null || true
	@sudo rm -f /usr/share/glib-2.0/schemas/xyz.shapemachine.castword-gnome.gschema.xml 2>/dev/null || true
	@sudo rm -f /usr/share/applications/xyz.shapemachine.castword-gnome.desktop 2>/dev/null || true
	@sudo rm -f /usr/share/metainfo/xyz.shapemachine.castword-gnome.metainfo.xml 2>/dev/null || true
	@sudo rm -f /usr/share/dbus-1/services/xyz.shapemachine.castword-gnome.service 2>/dev/null || true
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
	update-desktop-database $(APPLICATIONS_DIR) || echo "Warning: update-desktop-database failed — GNOME Shell may not pick up the desktop entry until you log out and back in"
endif
	@echo "Installed desktop file."

install-icons:
	mkdir -p $(ICONS_DEST_DIR)/scalable/apps
	cp $(ICONS_SRC_DIR)/scalable/apps/xyz.shapemachine.castword-gnome.svg \
	   $(ICONS_DEST_DIR)/scalable/apps/
ifeq ($(DESTDIR),)
	gtk-update-icon-cache -f -t $(ICONS_DEST_DIR) || echo "Warning: icon cache update failed — run 'gtk-update-icon-cache -f -t $(ICONS_DEST_DIR)' manually"
endif
	@echo "Installed icons."

uninstall-icons:
	rm -f $(ICONS_DEST_DIR)/scalable/apps/xyz.shapemachine.castword-gnome.svg
ifeq ($(DESTDIR),)
	gtk-update-icon-cache -f -t $(ICONS_DEST_DIR) || echo "Warning: icon cache update failed — run 'gtk-update-icon-cache -f -t $(ICONS_DEST_DIR)' manually"
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
	pkill -f 'castword[.]main' 2>/dev/null || true
	pkill -f '[/]bin/castword$$' 2>/dev/null || true
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
	# NOTE: appimagetool has no versioned releases upstream — 'continuous' is the only channel.
	# Verify the binary after download if supply-chain integrity is a concern.
	curl -L -o $(HOME)/bin/appimagetool \
	    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
	chmod +x $(HOME)/bin/appimagetool
	@echo ""
	@echo "Make sure ~/bin is in your PATH (add to ~/.config/fish/config.fish):"
	@echo "  fish_add_path ~/bin"

# Bump version, build all artifacts locally, then push and publish.
# Order: validate → bump → commit → tag → build → push → publish
# This ensures no remote state is modified until artifacts are confirmed good.
# Usage: make release VERSION=2026-04-03-00
release:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make release VERSION=2026-04-03-00)" && exit 1)
	@echo "$(VERSION)" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}-[0-9]{2}$$' || \
	    (echo "ERROR: VERSION must match format yyyy-mm-dd-NN (e.g. 2026-04-03-00)" && exit 1)
	@git rev-parse --abbrev-ref HEAD | grep -q '^main$$' || \
	    (echo "ERROR: make release must be run from the main branch" && exit 1)
	@echo "==> Bumping version to $(VERSION)"
	$(eval PYVER := $(subst -,.,$(VERSION)))
	sed -i 's/^version = ".*"/version = "$(PYVER)"/' pyproject.toml
	@TMPFILE=$$(mktemp); \
	printf 'castword-gnome ($(VERSION)-1) unstable; urgency=medium\n\n  * Release $(VERSION).\n\n -- Sri Rang <sri@shapemachine.xyz>  %s\n\n' \
	    "$$(date -R)" > $$TMPFILE; \
	cat packaging/debian/changelog >> $$TMPFILE; \
	mv $$TMPFILE packaging/debian/changelog
	@echo "==> Committing and tagging v$(VERSION) locally"
	git add pyproject.toml packaging/debian/changelog
	git commit -m "chore: release v$(VERSION)"
	git tag "v$(VERSION)"
	@echo "==> Building all artifacts locally (no remote changes yet)"
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) --skip-github --skip-aur
	@echo "==> Build succeeded — pushing to remote"
	git push origin main "v$(VERSION)" || \
	    (echo "ERROR: push failed. To retry after fixing: git push origin main v$(VERSION)" && exit 1)
	@echo "==> Publishing GitHub release and AUR"
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) \
	    --skip-flatpak --skip-appimage --skip-deb --skip-rpm --skip-pacman

# ─── Individual format targets ────────────────────────────────────────────────
# Build a single package format without cutting a full release.
# Usage: make deb VERSION=2026-04-03-00

tarball:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make tarball VERSION=2026-04-03-00)" && exit 1)
	mkdir -p dist/$(VERSION)
	git archive --prefix=castword-gnome-$(VERSION)/ HEAD \
	    | gzip > dist/$(VERSION)/castword-gnome-$(VERSION).tar.gz
	@echo "✓ Tarball → dist/$(VERSION)/castword-gnome-$(VERSION).tar.gz"

deb:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make deb VERSION=2026-04-03-00)" && exit 1)
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) \
	    --skip-flatpak --skip-appimage --skip-rpm --skip-pacman --skip-aur --skip-github

rpm:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make rpm VERSION=2026-04-03-00)" && exit 1)
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) \
	    --skip-flatpak --skip-appimage --skip-deb --skip-pacman --skip-aur --skip-github

appimage:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make appimage VERSION=2026-04-03-00)" && exit 1)
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) \
	    --skip-flatpak --skip-deb --skip-rpm --skip-pacman --skip-aur --skip-github

flatpak:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make flatpak VERSION=2026-04-03-00)" && exit 1)
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) \
	    --skip-appimage --skip-deb --skip-rpm --skip-pacman --skip-aur --skip-github

# Publish already-built artifacts in dist/<VERSION>/ to GitHub without rebuilding.
# Usage: make gh-release VERSION=2026-04-03-00
gh-release:
	@test -n "$(VERSION)" || (echo "ERROR: VERSION is required (e.g. make gh-release VERSION=2026-04-03-00)" && exit 1)
	PATH="$(HOME)/bin:$(PATH)" ./scripts/release.sh $(VERSION) \
	    --skip-flatpak --skip-appimage --skip-deb --skip-rpm --skip-pacman --skip-aur
