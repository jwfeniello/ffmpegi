"""PyInstaller entry point for ffmpegi.exe.

Path setup must happen before any project imports so that vocabulary.py
and the src/ modules are importable from the frozen bundle.
"""
from __future__ import annotations
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    _bundle = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    sys.path.insert(0, str(_bundle / 'src'))
    sys.path.insert(0, str(_bundle))

from cli import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
