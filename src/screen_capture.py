from __future__ import annotations
import platform
import re
import subprocess
from datetime import datetime
from pathlib import Path


def default_output_path() -> Path:
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    return Path.cwd() / f'screen_{ts}.mp4'


def list_audio_devices() -> list[dict]:
    """Return [{index, name}] for available audio inputs on this platform."""
    p = platform.system()
    if p == 'Windows':
        return _list_windows()
    if p == 'Darwin':
        return _list_macos()
    return _list_linux()


def build_record_args(
    output_path: Path,
    audio_device: str | None,
    duration: float | None,
    framerate: int = 30,
) -> list[str]:
    """Return an ffmpeg argv list for screen + optional audio recording."""
    p = platform.system()
    if p == 'Windows':
        return _args_windows(output_path, audio_device, duration, framerate)
    if p == 'Darwin':
        return _args_macos(output_path, audio_device, duration, framerate)
    return _args_linux(output_path, audio_device, duration, framerate)


# ---------------------------------------------------------------------------
# Windows  (GDI grab + DirectShow audio)
# ---------------------------------------------------------------------------

def _list_windows() -> list[dict]:
    try:
        r = subprocess.run(
            ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
            capture_output=True, text=True,
        )
        devices: list[dict] = []
        in_audio = False
        for line in r.stderr.splitlines():
            if 'DirectShow audio devices' in line:
                in_audio = True
                continue
            if 'DirectShow video devices' in line:
                in_audio = False
                continue
            if in_audio:
                m = re.search(r'"([^"]+)"', line)
                if m and 'Alternative name' not in line:
                    devices.append({'index': len(devices), 'name': m.group(1)})
        return devices
    except Exception:
        return []


def _args_windows(output_path, audio_device, duration, framerate):
    args = ['ffmpeg', '-y']
    if audio_device:
        args += ['-f', 'dshow', '-i', f'audio={audio_device}']
    args += ['-f', 'gdigrab', '-framerate', str(framerate), '-i', 'desktop']
    if duration:
        args += ['-t', str(duration)]
    args += ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
    if audio_device:
        args += ['-c:a', 'aac']
    args.append(str(output_path))
    return args


# ---------------------------------------------------------------------------
# macOS  (AVFoundation)
# ---------------------------------------------------------------------------

def _list_macos() -> list[dict]:
    try:
        r = subprocess.run(
            ['ffmpeg', '-f', 'avfoundation', '-list_devices', 'true', '-i', ''],
            capture_output=True, text=True,
        )
        devices: list[dict] = []
        in_audio = False
        for line in r.stderr.splitlines():
            if 'AVFoundation audio devices' in line:
                in_audio = True
                continue
            if 'AVFoundation video devices' in line:
                in_audio = False
                continue
            if in_audio:
                m = re.search(r'\[(\d+)\]\s+(.+)', line)
                if m:
                    devices.append({'index': int(m.group(1)), 'name': m.group(2).strip()})
        return devices
    except Exception:
        return []


def _args_macos(output_path, audio_device, duration, framerate):
    # avfoundation input: "screen_idx" or "screen_idx:audio_idx"
    inp = f'1:{audio_device}' if audio_device is not None else '1'
    args = ['ffmpeg', '-y', '-f', 'avfoundation', '-framerate', str(framerate), '-i', inp]
    if duration:
        args += ['-t', str(duration)]
    args += ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
    if audio_device is not None:
        args += ['-c:a', 'aac']
    args.append(str(output_path))
    return args


# ---------------------------------------------------------------------------
# Linux  (x11grab + PulseAudio / ALSA fallback)
# ---------------------------------------------------------------------------

def _list_linux() -> list[dict]:
    # Try PulseAudio / PipeWire-pulse
    try:
        r = subprocess.run(['pactl', 'list', 'sources', 'short'],
                           capture_output=True, text=True, check=True)
        devices: list[dict] = []
        for line in r.stdout.splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                devices.append({'index': len(devices), 'name': parts[1]})
        return devices
    except Exception:
        pass
    # Fallback: ALSA
    try:
        r = subprocess.run(['arecord', '-l'], capture_output=True, text=True, check=True)
        devices = []
        for line in r.stdout.splitlines():
            m = re.match(r'card (\d+): \S+ \[(.+?)\]', line)
            if m:
                devices.append({'index': len(devices),
                                'name': f'{m.group(2)} (hw:{m.group(1)},0)'})
        return devices
    except Exception:
        return []


def _args_linux(output_path, audio_device, duration, framerate):
    import os
    display = os.environ.get('DISPLAY', ':0.0')
    args = ['ffmpeg', '-y']
    if audio_device:
        args += ['-f', 'pulse', '-i', audio_device]
    args += ['-f', 'x11grab', '-framerate', str(framerate), '-i', display]
    if duration:
        args += ['-t', str(duration)]
    args += ['-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p']
    if audio_device:
        args += ['-c:a', 'aac']
    args.append(str(output_path))
    return args
