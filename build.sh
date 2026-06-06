#!/usr/bin/env bash
set -e

echo "Building ffmpegi (Linux) with PyInstaller..."

pyinstaller \
    --onefile \
    --name ffmpegi \
    --add-data "vocabulary.py:." \
    --add-data "src:src" \
    --hidden-import shlex \
    --hidden-import dataclasses \
    --hidden-import argparse \
    --hidden-import platform \
    --collect-all rapidfuzz \
    src/main.py

echo ""
echo "Done. Binary is at dist/ffmpegi"
echo "Copy it somewhere on your PATH, e.g.:"
echo "  sudo cp dist/ffmpegi /usr/local/bin/ffmpegi"
