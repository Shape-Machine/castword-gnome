---
name: castword-gnome-release
description: Build and publish a versioned release of castword-gnome to GitHub and AUR
---

# /castword-gnome-release

Build and publish a versioned release of castword-gnome to GitHub and AUR.

## Steps

### 1. Verify preconditions
- Confirm the working directory is the castword-gnome repo root.
- Run `git status` — abort if there are uncommitted changes. The release must be cut from a clean tree.
- Confirm the current branch is `main`.

### 2. Resolve the version
Version format: `yyyy-mm-dd-NN` where `NN` starts at `00` and increments for each additional release on the same calendar day (e.g. `2026-04-03-00`, `2026-04-03-01`).

- If a version argument was passed (e.g. `/castword-gnome-release 2026-04-03-00`), use it as-is.
- Otherwise, determine today's date (YYYY-MM-DD) and inspect existing git tags for that date prefix:
  ```
  git tag --list "v<date>-*" | sort | tail -1
  ```
  - If no tags exist for today: suggest `<date>-00`
  - If the latest is `<date>-NN`: suggest `<date>-<NN+1>` (zero-padded to 2 digits)

**Ask the user to confirm the resolved version before proceeding.**

### 3. Run `make release`
```
make release VERSION=<version>
```
This target:
1. Updates `version` in `pyproject.toml`
2. Prepends a new entry to `packaging/debian/changelog`
3. Commits `chore: release v<version>`
4. Tags `v<version>` and pushes tag + commit to `origin/main`
5. Builds `dist/castword-gnome-<version>.tar.gz` (source tarball)
6. Builds `dist/castword-gnome_<version>-1_all.deb` (Debian package)
7. Builds `dist/Castword-<version>-x86_64.AppImage`

If a build step fails (e.g. missing `dpkg-buildpackage` or `appimage-builder`), report which artifact failed, then continue with the remaining steps.

### 4. Run `make gh-release`
```
make gh-release VERSION=<version>
```
This creates a GitHub release from tag `v<version>` and uploads all files in `dist/`.

### 5. Run `make aur-release`
```
make aur-release VERSION=<version>
```
This target:
1. Converts the version to AUR pkgver format (`yyyy-mm-dd-NN` → `yyyy.mm.dd.NN`)
2. Fetches the sha256sum of the GitHub tag archive tarball
3. Updates `packaging/aur/PKGBUILD` and regenerates `.SRCINFO`
4. Commits the updated files to `main` and pushes
5. Clones `ssh://aur@aur.archlinux.org/castword-gnome.git`, copies in the updated files, commits, and pushes

If this step fails, report the error clearly (common cause: SSH key not registered on AUR account at https://aur.archlinux.org/account).

### 6. Update README download links
Open `README.md` and find the Packages table. Update the download links for:
- `.deb`: `https://github.com/Shape-Machine/castword-gnome/releases/download/v<version>/castword-gnome_<version>-1_all.deb`
- AppImage: `https://github.com/Shape-Machine/castword-gnome/releases/download/v<version>/Castword-<version>-x86_64.AppImage`
- Source tarball: `https://github.com/Shape-Machine/castword-gnome/releases/download/v<version>/castword-gnome-<version>.tar.gz`

Only add links for artifacts that actually exist in `dist/` — leave others as "coming soon".

Commit and push the README update:
```
git add README.md
git commit -m "docs: update download links for v<version>"
git push origin main
```

### 7. Print summary
Output:
```
✅ Released v<version>
Release URL: https://github.com/Shape-Machine/castword-gnome/releases/tag/v<version>
AUR: https://aur.archlinux.org/packages/castword-gnome

Artifacts:
  tarball    dist/castword-gnome-<version>.tar.gz
  .deb       dist/castword-gnome_<version>-1_all.deb   (or: not built)
  AppImage   dist/Castword-<version>-x86_64.AppImage   (or: not built)
```

## Notes
- Flathub submission is a separate manual PR to flathub/flathub — remind the user.
- If `appimage-builder` is not installed: `pip install appimage-builder`
- If `dpkg-buildpackage` is not installed: `sudo apt install build-essential devscripts debhelper`
