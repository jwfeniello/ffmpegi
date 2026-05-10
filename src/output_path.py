from __future__ import annotations
from pathlib import Path
from models import EditPlan
from builder import PRESET_OUTPUT


def derive_output_path(plan: EditPlan, input_path: Path) -> Path:
    """Derive an output path from an EditPlan when -o is not specified.

    Priority for suffix: trim > resize > compress.
    Extension: target_format if a conversion is requested, else original ext.
    Never returns a path equal to input_path — appends _out if needed.
    """
    stem = input_path.stem
    original_ext = input_path.suffix  # includes dot, e.g. '.mp4'

    is_merge = len(plan.inputs) > 1

    if plan.extract_audio:
        fmt = plan.audio_format or 'mp3'
        out = input_path.parent / f"{stem}.{fmt}"

    elif is_merge:
        fmt = plan.target_format or original_ext.lstrip('.')
        out = input_path.parent / f"merged.{fmt}"

    else:
        is_trim = plan.trim_start is not None or plan.trim_end is not None
        is_resize = bool(plan.target_resolution)
        is_compress = plan.target_filesize_mb is not None or bool(plan.target_preset)

        if is_trim:
            suffix = '_trimmed'
        elif is_resize:
            suffix = f'_{plan.target_resolution}'
        elif is_compress:
            suffix = '_compressed'
        else:
            suffix = ''

        if plan.target_preset and plan.target_preset in PRESET_OUTPUT:
            out_ext = f".{PRESET_OUTPUT[plan.target_preset][0]}"
        elif plan.target_format:
            out_ext = f".{plan.target_format}"
        else:
            out_ext = original_ext
        out = input_path.parent / f"{stem}{suffix}{out_ext}"

    if out == input_path:
        out = input_path.parent / f"{stem}_out{original_ext}"

    return out
