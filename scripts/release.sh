#!/usr/bin/env bash
# Usage: ./scripts/release.sh <version> [--skip-flatpak] [--skip-appimage] [--skip-deb] [--skip-rpm] [--skip-pacman] [--skip-aur] [--skip-github]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# ── Args ──────────────────────────────────────────────────────────────────────

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
    echo "Usage: $0 <version> [--skip-flatpak] [--skip-appimage] [--skip-deb] [--skip-rpm] [--skip-pacman] [--skip-aur] [--skip-github]"
    exit 1
fi
shift

DO_FLATPAK=1 DO_APPIMAGE=1 DO_DEB=1 DO_RPM=1 DO_PACMAN=1 DO_AUR=1 DO_GITHUB=1
for arg in "$@"; do
    case "$arg" in
        --skip-flatpak)  DO_FLATPAK=0  ;;
        --skip-appimage) DO_APPIMAGE=0 ;;
        --skip-deb)      DO_DEB=0      ;;
        --skip-rpm)      DO_RPM=0      ;;
        --skip-pacman)   DO_PACMAN=0   ;;
        --skip-aur)      DO_AUR=0      ;;
        --skip-github)   DO_GITHUB=0   ;;
    esac
done

APP_ID="xyz.shapemachine.castword-gnome"
DIST="$ROOT/dist/$VERSION"
mkdir -p "$DIST"

log()  { echo "▶ $*"; }
ok()   { echo "✓ $*"; }
skip() { echo "– $* (skipped)"; }

# ── Check tools ───────────────────────────────────────────────────────────────

check() {
    command -v "$1" &>/dev/null || { echo "✗ missing: $1 — $2"; exit 1; }
}

check uv "sudo pacman -S uv"
[[ $DO_FLATPAK  == 1 ]] && check flatpak-builder "sudo pacman -S flatpak-builder"
[[ $DO_APPIMAGE == 1 ]] && check appimagetool    "download from https://github.com/AppImage/appimagetool/releases (see make release-deps)"
[[ $DO_DEB      == 1 ]] && check fpm             "sudo gem install fpm  (see make release-deps)"
[[ $DO_RPM      == 1 ]] && check fpm             "sudo gem install fpm  (see make release-deps)"
[[ $DO_PACMAN   == 1 ]] && check fpm             "sudo gem install fpm  (see make release-deps)"
[[ $DO_AUR      == 1 ]] && check makepkg         "install base-devel"
[[ $DO_AUR      == 1 ]] && check git             "sudo pacman -S git"
[[ $DO_GITHUB   == 1 ]] && check gh              "sudo pacman -S github-cli"

# ── 1. Stage install tree ─────────────────────────────────────────────────────

STAGING="$ROOT/_release_staging"
log "Staging install tree (prefix=/usr, version=$VERSION)"
rm -rf "$STAGING"

# Python package
mkdir -p "$STAGING/usr/share/castword-gnome"
cp -r "$ROOT/castword" "$STAGING/usr/share/castword-gnome/"

# Vendor pip dependencies (not in all distro repos)
log "Vendoring pip dependencies"
uv pip install --quiet \
    --python python3 \
    --target="$STAGING/usr/share/castword-gnome/vendor" \
    "httpx==0.28.1" "openai==2.30.0" "anthropic==0.89.0" "google-genai==1.70.0"

# Launcher script
mkdir -p "$STAGING/usr/bin"
cat > "$STAGING/usr/bin/castword" <<'LAUNCHER'
#!/bin/bash
export PYTHONPATH="/usr/share/castword-gnome/vendor:/usr/share/castword-gnome:${PYTHONPATH:-}"
exec python3 -c "from castword.main import main; main()" "$@"
LAUNCHER
chmod +x "$STAGING/usr/bin/castword"

# XDG integration files
mkdir -p \
    "$STAGING/usr/share/applications" \
    "$STAGING/usr/share/glib-2.0/schemas" \
    "$STAGING/usr/share/metainfo" \
    "$STAGING/usr/share/dbus-1/services"

mkdir -p "$STAGING/usr/share/icons/hicolor/scalable/apps"
cp "$ROOT/data/icons/hicolor/scalable/apps/$APP_ID.svg" \
   "$STAGING/usr/share/icons/hicolor/scalable/apps/"

cp "$ROOT/data/$APP_ID.desktop"     "$STAGING/usr/share/applications/"
cp "$ROOT/data/$APP_ID.gschema.xml" "$STAGING/usr/share/glib-2.0/schemas/"
cp "$ROOT/data/$APP_ID.metainfo.xml" "$STAGING/usr/share/metainfo/"

# D-Bus service file — substitute absolute Exec path
sed "s|Exec=.*|Exec=/usr/bin/castword|" \
    "$ROOT/data/$APP_ID.service" \
    > "$STAGING/usr/share/dbus-1/services/$APP_ID.service"

ok "Staging complete → $STAGING"

# ── 2. Flatpak ────────────────────────────────────────────────────────────────

if [[ $DO_FLATPAK == 1 ]]; then
    log "Building Flatpak"
    FLATPAK_REPO="$ROOT/_flatpak_repo"
    FLATPAK_BUILD="$ROOT/_flatpak_build"
    rm -rf "$FLATPAK_BUILD"

    flatpak-builder \
        --force-clean \
        --repo="$FLATPAK_REPO" \
        "$FLATPAK_BUILD" \
        "$ROOT/packaging/flatpak/$APP_ID.yml"

    flatpak build-bundle \
        "$FLATPAK_REPO" \
        "$DIST/$APP_ID-$VERSION.flatpak" \
        "$APP_ID"

    ok "Flatpak → $DIST/$APP_ID-$VERSION.flatpak"
else
    skip "Flatpak"
fi

# ── 3. AppImage ───────────────────────────────────────────────────────────────

if [[ $DO_APPIMAGE == 1 ]]; then
    log "Building AppImage"
    APPDIR="$ROOT/_appimage/$APP_ID.AppDir"
    rm -rf "$ROOT/_appimage"
    mkdir -p "$APPDIR"

    # Copy staged files into AppDir
    cp -r "$STAGING/usr/"* "$APPDIR/"

    # AppDir root metadata (required by AppImage spec)
    cp "$STAGING/usr/share/applications/$APP_ID.desktop" "$APPDIR/$APP_ID.desktop"
    cp "$STAGING/usr/share/icons/hicolor/scalable/apps/$APP_ID.svg" "$APPDIR/$APP_ID.svg"

    cat > "$APPDIR/AppRun" <<'APPRUN'
#!/bin/bash
HERE="$(dirname "$(readlink -f "$0")")"

# Check for required system libraries before launching
missing=()
python3 -c "import gi; gi.require_version('Gtk','4.0'); from gi.repository import Gtk" 2>/dev/null \
    || missing+=("GTK4 + python-gobject")
python3 -c "import gi; gi.require_version('Adw','1'); from gi.repository import Adw" 2>/dev/null \
    || missing+=("libadwaita")

if [[ ${#missing[@]} -gt 0 ]]; then
    echo "castword requires: ${missing[*]}"
    echo ""
    echo "Install with:"
    echo "  Ubuntu/Debian:  sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-0"
    echo "  Fedora:         sudo dnf install python3-gobject gtk4 libadwaita"
    echo "  Arch:           sudo pacman -S python-gobject gtk4 libadwaita"
    exit 1
fi

export PYTHONPATH="$HERE/share/castword-gnome/vendor:$HERE/share/castword-gnome:${PYTHONPATH:-}"
export XDG_DATA_DIRS="$HERE/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
export GSETTINGS_SCHEMA_DIR="$HERE/share/glib-2.0/schemas"
exec python3 -c "from castword.main import main; main()" "$@"
APPRUN
    chmod +x "$APPDIR/AppRun"

    ARCH=x86_64 appimagetool "$APPDIR" "$DIST/Castword-$VERSION-x86_64.AppImage"
    ok "AppImage → $DIST/Castword-$VERSION-x86_64.AppImage"
else
    skip "AppImage"
fi

# ── 4. .deb ───────────────────────────────────────────────────────────────────

if [[ $DO_DEB == 1 ]]; then
    log "Building .deb"
    fpm \
        -s dir \
        -t deb \
        -n castword-gnome \
        -v "$VERSION" \
        --description "GNOME overlay for LLM-powered text tone rewriting" \
        --url "https://shapemachine.xyz/castword" \
        --maintainer "Sri Rang <sri@shapemachine.xyz>" \
        --depends "python3" \
        --depends "python3-gi" \
        --depends "gir1.2-gtk-4.0" \
        --depends "gir1.2-adw-1" \
        --depends "libsecret-1-0" \
        --after-install "$ROOT/packaging/debian/postinst" \
        --package "$DIST/castword-gnome-$VERSION.deb" \
        -C "$STAGING" \
        usr
    ok ".deb → $DIST/castword-gnome-$VERSION.deb"
else
    skip ".deb"
fi

# ── 5. .rpm ───────────────────────────────────────────────────────────────────

if [[ $DO_RPM == 1 ]]; then
    log "Building .rpm"
    fpm \
        -s dir \
        -t rpm \
        -n castword-gnome \
        -v "$VERSION" \
        --description "GNOME overlay for LLM-powered text tone rewriting" \
        --url "https://shapemachine.xyz/castword" \
        --maintainer "Sri Rang <sri@shapemachine.xyz>" \
        --depends "python3" \
        --depends "python3-gobject" \
        --depends "gtk4" \
        --depends "libadwaita" \
        --depends "libsecret" \
        --package "$DIST/castword-gnome-$VERSION.rpm" \
        -C "$STAGING" \
        usr
    ok ".rpm → $DIST/castword-gnome-$VERSION.rpm"
else
    skip ".rpm"
fi

# ── 6. .pkg.tar.zst (Arch / CachyOS) ─────────────────────────────────────────

if [[ $DO_PACMAN == 1 ]]; then
    log "Building Arch package (.pkg.tar.zst)"
    fpm \
        -s dir \
        -t pacman \
        -n castword-gnome \
        -v "$VERSION" \
        --architecture any \
        --description "GNOME overlay for LLM-powered text tone rewriting" \
        --url "https://shapemachine.xyz/castword" \
        --maintainer "Sri Rang <sri@shapemachine.xyz>" \
        --depends "python" \
        --depends "python-gobject" \
        --depends "gtk4" \
        --depends "libadwaita" \
        --depends "libsecret" \
        --package "$DIST/castword-gnome-$VERSION-any.pkg.tar.zst" \
        -C "$STAGING" \
        usr
    ok "Arch package → $DIST/castword-gnome-$VERSION-any.pkg.tar.zst"
else
    skip "Arch package"
fi

# ── 7. AUR (castword-gnome-bin) ───────────────────────────────────────────────

if [[ $DO_AUR == 1 ]]; then
    log "Publishing AUR package (castword-gnome-bin)"

    PKG_FILE="$DIST/castword-gnome-$VERSION-any.pkg.tar.zst"
    if [[ ! -f "$PKG_FILE" ]]; then
        echo "✗ AUR publish requires the Arch package — re-run without --skip-pacman"
        exit 1
    fi

    SHA256=$(sha256sum "$PKG_FILE" | awk '{print $1}')
    PKGVER="${VERSION//-/.}"

    AUR_TMP=$(mktemp -d)
    trap 'rm -rf "$AUR_TMP"' EXIT

    log "Cloning AUR repo (castword-gnome-bin)"
    git clone ssh://aur@aur.archlinux.org/castword-gnome-bin.git "$AUR_TMP"

    sed "s/@VERSION@/$VERSION/g; s/@PKGVER@/$PKGVER/g; s/@SHA256SUM@/$SHA256/g" \
        "$ROOT/packaging/aur/PKGBUILD" > "$AUR_TMP/PKGBUILD"

    cp "$ROOT/packaging/aur/castword-gnome-bin.install" "$AUR_TMP/castword-gnome-bin.install"

    (cd "$AUR_TMP" && makepkg --printsrcinfo > .SRCINFO)

    git -C "$AUR_TMP" add PKGBUILD .SRCINFO castword-gnome-bin.install
    git -C "$AUR_TMP" commit -m "Update to v$VERSION"
    git -C "$AUR_TMP" push

    ok "AUR published → https://aur.archlinux.org/packages/castword-gnome-bin"
else
    skip "AUR"
fi

# ── 8. GitHub release ─────────────────────────────────────────────────────────

if [[ $DO_GITHUB == 1 ]]; then
    log "Publishing GitHub release v$VERSION"
    ASSETS=()
    for f in "$DIST"/*; do
        [[ -f "$f" ]] && ASSETS+=("$f")
    done

    PREV_TAG=$(git describe --tags --abbrev=0 "v$VERSION^" 2>/dev/null || echo "")
    if [[ -n "$PREV_TAG" ]]; then
        NOTES=$(git log "$PREV_TAG..v$VERSION" --pretty=format:"- %s" --no-merges)
    else
        NOTES=$(git log "v$VERSION" --pretty=format:"- %s" --no-merges)
    fi

    gh release create "v$VERSION" \
        --repo Shape-Machine/castword-gnome \
        --title "v$VERSION" \
        --notes "$NOTES" \
        "${ASSETS[@]}"

    ok "GitHub release → https://github.com/Shape-Machine/castword-gnome/releases/tag/v$VERSION"
else
    skip "GitHub release"
fi

# ── Done ──────────────────────────────────────────────────────────────────────

echo ""
echo "────────────────────────────────────────"
echo "  Release $VERSION complete"
echo "  Artifacts in: $DIST"
ls -lh "$DIST"
echo "────────────────────────────────────────"
