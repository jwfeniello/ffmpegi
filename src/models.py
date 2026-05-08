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


@dataclass
class ClarificationError:
    reason: str
    code: str | None = None
    options: list[str] | None = None
