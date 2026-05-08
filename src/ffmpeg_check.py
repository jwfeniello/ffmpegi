from __future__ import annotations
import shutil


def check_ffmpeg() -> None:
    missing = [t for t in ('ffmpeg', 'ffprobe') if not shutil.which(t)]
    if missing:
        tools = ' and '.join(missing)
        raise SystemExit(
            f"{tools} not found. Install with: winget install Gyan.FFmpeg"
        )
