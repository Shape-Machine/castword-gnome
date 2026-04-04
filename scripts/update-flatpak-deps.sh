#!/usr/bin/env bash
# Regenerate packaging/flatpak/castword-pip-deps.yaml using flatpak-pip-generator.
# Run this whenever pip dependency versions change in pyproject.toml.
#
# Requirements: uv, flatpak (org.gnome.Sdk//47 installed)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GENERATOR_URL="https://raw.githubusercontent.com/flatpak/flatpak-builder-tools/master/pip/flatpak-pip-generator.py"
GENERATOR=/tmp/flatpak-pip-generator.py
VENV=/tmp/fpg-env

echo "▶ Setting up flatpak-pip-generator"
curl -sL "$GENERATOR_URL" -o "$GENERATOR"
uv venv "$VENV" --clear --python 3.13 >/dev/null 2>&1
uv pip install --python "$VENV/bin/python" requirements-parser packaging PyYAML >/dev/null 2>&1

echo "▶ Generating castword-pip-deps.yaml"
cd /tmp
"$VENV/bin/python" "$GENERATOR" \
    --runtime org.gnome.Sdk//47 \
    --output castword-pip-deps \
    --yaml \
    "httpx==0.28.1" "openai==2.30.0" "anthropic==0.89.0" "google-genai==1.70.0"

cp /tmp/castword-pip-deps.yaml "$ROOT/packaging/flatpak/castword-pip-deps.yaml"
echo "✓ Updated packaging/flatpak/castword-pip-deps.yaml"
echo ""
echo "⚠️  Post-generation step required:"
echo "   flatpak-pip-generator downloads source tarballs for Rust-compiled packages"
echo "   (jiter, pydantic-core, cffi, cryptography, charset-normalizer, websockets)."
echo "   These fail to build inside the GNOME SDK sandbox (no maturin/Rust toolchain)."
echo "   Manually replace those .tar.gz entries with pre-built manylinux wheels from PyPI:"
echo "     jiter         → cp312 manylinux_2_17_x86_64 .whl"
echo "     pydantic-core → cp312 manylinux_2_17_x86_64 .whl"
echo "     cffi          → cp312 manylinux2014_x86_64 .whl"
echo "     cryptography  → cp311-abi3 manylinux_2_28_x86_64 .whl"
echo "     charset-normalizer → cp312 manylinux2014_x86_64 .whl"
echo "     websockets    → py3-none-any .whl"
echo "   Look up URLs/sha256 on https://pypi.org/pypi/<package>/<version>/json"
