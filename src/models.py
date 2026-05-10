from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EditPlan:
    inputs: list[Path] = field(default_factory=list)
    trim_start: float | None = None
    trim_end: float | None = None
    target_resolution: str | None = None
    target_format: str | None = None
    target_filesize_mb: float | None = None
    target_preset: str | None = None
    extract_audio: bool = False
    audio_format: str | None = None
    # yt-dlp download fields
    download_url: str | None = None
    download_quality: str | None = None       # "1080p","720p","best","worst"
    download_format: str | None = None        # video container: "mp4","mkv","webm"
    download_audio_only: bool = False         # -x flag
    download_audio_format: str | None = None  # "mp3","wav","m4a","flac","aac","opus"
    download_subs: bool = False
    download_sub_lang: str | None = None      # "en","es",… default "en"
    download_sub_auto: bool = False           # auto-generated subs
    download_playlist: bool | None = None     # None=default, True=force, False=single
    download_thumbnail: bool = False
    download_metadata: bool = False


@dataclass
class ClarificationError:
    reason: str
    code: str | None = None
    options: list[str] | None = None
