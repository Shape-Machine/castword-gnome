---
name: castword-gnome-release
description: Build and publish a versioned release of castword-gnome to GitHub and AUR
---

# /castword-gnome-release

Build and publish a versioned release of castword-gnome to GitHub, AUR, and all package formats.

## Steps

### 1. Verify preconditions
- Confirm the working directory is the castword-gnome repo root.
- Run `git status` — abort if there are uncommitted changes.
- Confirm the current branch is `main`.
- Check that release tools are installed: `flatpak-builder`, `appimagetool`, `fpm`, `gh`.
  If any are missing, tell the user to run `make release-deps` first and abort.

### 2. Resolve the version
Version format: `yyyy-mm-dd-NN` where `NN` starts at `00` and increments for each additional release on the same calendar day.

- If a version argument was passed, use it as-is.
- Otherwise, check existing git tags:
  ```
  git tag --list "v<today>-*" | sort | tail -1
  ```
  - No tags for today → suggest `<today>-00`
  - Latest is `<today>-NN` → suggest `<today>-<NN+1>` (zero-padded)

**Ask the user to confirm the resolved version before proceeding.**

### 3. Run `make release`
```
make release VERSION=<version>
```
This single target:
1. Bumps `version` in `pyproject.toml` and prepends an entry to `packaging/debian/changelog`
2. Commits `chore: release v<version>`, tags `v<version>`, pushes to `origin/main`
3. Calls `scripts/release.sh <version>` which:
   - Stages the install tree (Python package + vendored deps + XDG files)
   - Builds Flatpak (`.flatpak`)
   - Builds AppImage (`Castword-<version>-x86_64.AppImage`) via `appimagetool`
   - Builds `.deb` via `fpm`
   - Builds `.rpm` via `fpm`
   - Builds `.pkg.tar.zst` (Arch/CachyOS) via `fpm`
   - Publishes `castword-gnome-bin` to AUR (from the `.pkg.tar.zst` checksum)
   - Creates the GitHub release with all artifacts attached

If any build step fails, report what failed and stop — do not partially publish.

### 4. Update README download links
Open `README.md` and update the Packages table with links to all artifacts in `dist/<version>/`:
- Source tarball: use the GitHub release tag archive URL
- `.deb`, AppImage, `.flatpak`: direct links to `releases/download/v<version>/...`
- AUR: update to `yay -S castword-gnome-bin`

Commit and push:
```
git add README.md
git commit -m "docs: update download links for v<version>"
git push origin main
```

### 5. Print summary
```
✅ Released v<version>
Release URL: https://github.com/Shape-Machine/castword-gnome/releases/tag/v<version>
AUR: https://aur.archlinux.org/packages/castword-gnome-bin

Artifacts:
  .deb         dist/<version>/castword-gnome-<version>.deb
  .rpm         dist/<version>/castword-gnome-<version>.rpm
  .pkg.tar.zst dist/<version>/castword-gnome-<version>-any.pkg.tar.zst
  AppImage     dist/<version>/Castword-<version>-x86_64.AppImage
  Flatpak      dist/<version>/xyz.shapemachine.castword-gnome-<version>.flatpak
```

## Notes
- Run `make release-deps` once on a new machine before the first release.
- Flathub submission (PR to flathub/flathub) is a separate manual step — remind the user.
- The release script accepts `--skip-*` flags if you need to skip a format:
  `./scripts/release.sh <version> --skip-flatpak --skip-rpm`
