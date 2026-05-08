from __future__ import annotations


def compute_video_bitrate(
    filesize_mb: float,
    duration_s: float,
    audio_kbps: int = 128,
) -> int:
    """Compute target video bitrate in kbps for a given filesize budget.

    Formula: total_kbps = filesize_mb * 8192 / duration_s
             video_kbps = total_kbps - audio_kbps
    Clamped to a minimum of 50 kbps to avoid unusable output.
    """
    if duration_s <= 0:
        raise ValueError("duration_s must be > 0")
    total_kbps = (filesize_mb * 8192) / duration_s
    video_kbps = total_kbps - audio_kbps
    return max(50, int(video_kbps))
