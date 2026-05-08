from __future__ import annotations
import subprocess
from pathlib import Path

from models import EditPlan
from compute import compute_video_bitrate


_VIDEO_CODECS: dict[str, str] = {
    'mp4': 'libx264', 'mkv': 'libx264', 'mov': 'libx264',
    'webm': 'libvpx-vp9', 'avi': 'mpeg4', 'flv': 'libx264', 'wmv': 'wmv2',
}
_AUDIO_CODECS: dict[str, str] = {
    'mp4': 'aac', 'mkv': 'aac', 'mov': 'aac',
    'webm': 'libopus', 'avi': 'libmp3lame', 'flv': 'aac', 'wmv': 'wmv2',
}
_AUDIO_EXTRACT_CODECS: dict[str, str] = {
    'mp3': 'libmp3lame', 'wav': 'pcm_s16le', 'm4a': 'aac',
    'aac': 'aac', 'flac': 'flac', 'ogg': 'libvorbis', 'opus': 'libopus',
}
_RES_HEIGHT: dict[str, int] = {
    '144p': 144, '240p': 240, '360p': 360, '480p': 480,
    '720p': 720, '1080p': 1080, '1440p': 1440, '2160p': 2160, '4320p': 4320,
}


def get_video_duration(path: Path) -> float:
    """Call ffprobe to get duration in seconds."""
    result = subprocess.run(
        [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


def build_ffmpeg_args(
    plan: EditPlan,
    output_path: Path,
    video_duration: float | None = None,
) -> list[str]:
    """Build an ffmpeg argv list from an EditPlan.

    Never builds a shell string -- always returns a list[str].
    audio_format=None defaults to 'mp3' for audio extraction.
    """
    args: list[str] = ['ffmpeg', '-y']
    is_merge = len(plan.inputs) > 1

    if is_merge:
        for f in plan.inputs:
            args += ['-i', str(f)]
        n = len(plan.inputs)
        filter_in = ''.join(f'[{i}:v][{i}:a]' for i in range(n))
        filter_str = f'{filter_in}concat=n={n}:v=1:a=1[v][a]'
        args += ['-filter_complex', filter_str, '-map', '[v]', '-map', '[a]']
        args.append(str(output_path))
        return args

    input_path = plan.inputs[0] if plan.inputs else None

    # Fast seek: -ss before -i
    if plan.trim_start is not None:
        args += ['-ss', str(plan.trim_start)]

    if input_path:
        args += ['-i', str(input_path)]

    # Duration after input
    if plan.trim_start is not None and plan.trim_end is not None:
        duration = plan.trim_end - plan.trim_start
        args += ['-to', str(duration)]

    if plan.extract_audio:
        args.append('-vn')
        fmt = plan.audio_format or 'mp3'
        codec = _AUDIO_EXTRACT_CODECS.get(fmt, 'libmp3lame')
        args += ['-c:a', codec]
        args.append(str(output_path))
        return args

    vf_parts: list[str] = []
    if plan.target_resolution:
        h = _RES_HEIGHT.get(plan.target_resolution, 720)
        vf_parts.append(f'scale=-2:{h}')
    if vf_parts:
        args += ['-vf', ','.join(vf_parts)]

    out_ext = output_path.suffix.lstrip('.').lower()
    fmt_key = plan.target_format or out_ext or 'mp4'
    v_codec = _VIDEO_CODECS.get(fmt_key, 'libx264')
    a_codec = _AUDIO_CODECS.get(fmt_key, 'aac')
    args += ['-c:v', v_codec, '-c:a', a_codec]

    if plan.target_filesize_mb is not None:
        dur = video_duration
        if dur is None and input_path:
            dur = get_video_duration(input_path)
        if dur and dur > 0:
            kbps = compute_video_bitrate(plan.target_filesize_mb, dur)
            args += ['-b:v', f'{kbps}k', '-b:a', '128k']

    args.append(str(output_path))
    return args
