from __future__ import annotations
import subprocess
from pathlib import Path

from models import EditPlan
from compute import compute_video_bitrate


# Preset → (container, video_codec, audio_codec).
# When a preset is active these values always win, regardless of input container.
PRESET_OUTPUT: dict[str, tuple[str, str, str]] = {
    'discord':   ('mp4', 'libx264', 'aac'),
    'youtube':   ('mp4', 'libx264', 'aac'),
    'mobile':    ('mp4', 'libx264', 'aac'),
    'twitter':   ('mp4', 'libx264', 'aac'),
    'instagram': ('mp4', 'libx264', 'aac'),
    'whatsapp':  ('mp4', 'libx264', 'aac'),
    'telegram':  ('mp4', 'libx264', 'aac'),
    'email':     ('mp4', 'libx264', 'aac'),
}

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


def build_ytdlp_args(plan: EditPlan, output_dir: Path) -> list[str]:
    """Build a yt-dlp argv list from an EditPlan.

    Side-effect: clears plan.trim_start / plan.trim_end when a download
    section is emitted, so the subsequent ffmpeg pass does not re-trim.
    """
    assert plan.download_url, "build_ytdlp_args called without download_url"
    args: list[str] = ['yt-dlp']

    # Quality / format selection
    if plan.download_audio_only:
        args.append('-x')
        if plan.download_audio_format:
            args += ['--audio-format', plan.download_audio_format]
    elif plan.download_quality in ('best', None):
        args += ['-f', 'bestvideo+bestaudio/best']
    elif plan.download_quality == 'worst':
        args += ['-f', 'worst']
    elif plan.download_quality and plan.download_quality.endswith('p'):
        h = plan.download_quality[:-1]
        args += ['-f', f'bestvideo[height<={h}]+bestaudio/best[height<={h}]']

    # Container remux
    if plan.download_format and not plan.download_audio_only:
        args += ['--merge-output-format', plan.download_format]
        args += ['--remux-video', plan.download_format]

    # Section download (consumes trim so ffmpeg doesn't re-trim)
    if plan.trim_start is not None or plan.trim_end is not None:
        start = plan.trim_start or 0.0
        end_str = f'{plan.trim_end:.3f}' if plan.trim_end is not None else 'inf'
        args += ['--download-sections', f'*{start:.3f}-{end_str}']
        plan.trim_start = None
        plan.trim_end = None

    # Subtitles
    if plan.download_subs:
        if plan.download_sub_auto:
            args.append('--write-auto-subs')
        else:
            args.append('--write-subs')
        lang = plan.download_sub_lang or 'en'
        args += ['--sub-langs', lang, '--convert-subs', 'srt']

    # Playlist behaviour
    if plan.download_playlist is True:
        args.append('--yes-playlist')
    elif plan.download_playlist is False:
        args.append('--no-playlist')

    # Extras
    if plan.download_thumbnail:
        args += ['--embed-thumbnail', '--write-thumbnail']
    if plan.download_metadata:
        args.append('--embed-metadata')

    # Output template
    args += ['-o', str(output_dir / '%(title)s.%(ext)s')]

    # Capture final filepath on stdout; --progress re-enables bar in quiet mode
    args += ['--print', 'after_move:%(filepath)s', '--progress', '--no-simulate']

    args.append(plan.download_url)
    return args


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

    # --- resize ---
    if plan.target_resolution:
        h = _RES_HEIGHT.get(plan.target_resolution, 720)
        vf_parts.append(f'scale=-2:{h}')
    elif plan.target_width and plan.target_height:
        vf_parts.append(f'scale={plan.target_width}:{plan.target_height}')
    elif plan.target_width:
        vf_parts.append(f'scale={plan.target_width}:-2')
    elif plan.target_height:
        vf_parts.append(f'scale=-2:{plan.target_height}')
    elif plan.target_scale_pct is not None:
        f = plan.target_scale_pct / 100.0
        vf_parts.append(f'scale=iw*{f:.4f}:ih*{f:.4f}')

    # --- crop ---
    if plan.crop_aspect:
        w_r, h_r = (int(x) for x in plan.crop_aspect.split(':'))
        # Center-crop to aspect ratio: keep full height, clip width (or vice-versa)
        vf_parts.append(
            f'crop=if(gt(iw/ih\\,{w_r}/{h_r})\\,ih*{w_r}/{h_r}\\,iw):'
            f'if(gt(iw/ih\\,{w_r}/{h_r})\\,ih\\,iw*{h_r}/{w_r})'
        )
    elif plan.crop_w or plan.crop_h:
        cw = str(plan.crop_w) if plan.crop_w else 'iw'
        ch = str(plan.crop_h) if plan.crop_h else 'ih'
        cx = str(plan.crop_x) if plan.crop_x is not None else f'(iw-{cw})/2'
        cy = str(plan.crop_y) if plan.crop_y is not None else f'(ih-{ch})/2'
        vf_parts.append(f'crop={cw}:{ch}:{cx}:{cy}')

    if vf_parts:
        args += ['-vf', ','.join(vf_parts)]

    if plan.target_preset and plan.target_preset in PRESET_OUTPUT:
        _, v_codec, a_codec = PRESET_OUTPUT[plan.target_preset]
    else:
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
