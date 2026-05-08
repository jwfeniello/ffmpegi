from __future__ import annotations
import re
import subprocess
import sys


_TIME_RE = re.compile(r'time=(\d{2}:\d{2}:\d{2}(?:\.\d+)?)')


def _hms_to_secs(hms: str) -> float:
    parts = hms.split(':')
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])


def _secs_to_hms(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = secs % 60
    return f"{h:02d}:{m:02d}:{s:05.2f}"


def run_ffmpeg(
    args: list[str],
    video_duration: float | None = None,
    verbose: bool = False,
) -> int:
    """Run ffmpeg, stream stderr, show inline time= progress.

    Returns ffmpeg's exit code.
    On failure (non-zero exit) prints the last 20 stderr lines unless verbose
    mode already showed them all.
    """
    proc = subprocess.Popen(args, stderr=subprocess.PIPE, text=True, bufsize=0)
    assert proc.stderr is not None

    last_20: list[str] = []
    buf = ''
    showed_progress = False

    while True:
        chunk = proc.stderr.read(256)
        if not chunk:
            break
        buf += chunk
        lines = re.split(r'[\r\n]', buf)
        for line in lines[:-1]:
            line = line.strip()
            if not line:
                continue
            last_20.append(line)
            if len(last_20) > 20:
                last_20.pop(0)

            m = _TIME_RE.search(line)
            if m:
                showed_progress = True
                elapsed = m.group(1)
                if video_duration:
                    elapsed_secs = _hms_to_secs(elapsed)
                    pct = min(100, int(elapsed_secs / video_duration * 100))
                    dur_str = _secs_to_hms(video_duration)
                    print(f"\rtime={elapsed} / {dur_str} ({pct}%)", end='', flush=True)
                else:
                    print(f"\rtime={elapsed}", end='', flush=True)
            elif verbose:
                print(line, file=sys.stderr)

        buf = lines[-1]

    if buf.strip():
        last_20.append(buf.strip())
        if len(last_20) > 20:
            last_20.pop(0)

    proc.wait()

    if showed_progress:
        print()  # newline after final progress line

    if proc.returncode != 0 and not verbose:
        print("\nFFmpeg error output:", file=sys.stderr)
        for line in last_20:
            print(line, file=sys.stderr)

    return proc.returncode
