from __future__ import annotations
import argparse
import dataclasses
import shlex
import sys
from pathlib import Path

# Ensure project root (vocabulary.py) and src/ (models, parser, …) are importable
# whether running from source or as a PyInstaller bundle.
if getattr(sys, 'frozen', False):
    _bundle = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    sys.path.insert(0, str(_bundle / 'src'))
    sys.path.insert(0, str(_bundle))
else:
    _root = Path(__file__).parent.parent
    sys.path.insert(0, str(Path(__file__).parent))  # src/
    sys.path.insert(0, str(_root))                   # project root

from parser import parse                             # noqa: E402
from builder import build_ffmpeg_args, get_video_duration  # noqa: E402
from models import EditPlan, ClarificationError      # noqa: E402
from output_path import derive_output_path           # noqa: E402
from runner import run_ffmpeg                        # noqa: E402
from ffmpeg_check import check_ffmpeg                # noqa: E402
from vocabulary import FILESIZE_PATTERNS             # noqa: E402

VIDEO_EXTS = frozenset({
    '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv',
    '.wmv', '.m4v', '.mpg', '.mpeg', '.ts',
})
AUDIO_EXTS = frozenset({
    '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.opus',
})
MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS


def split_request_and_files(tokens: list[str]) -> tuple[str, list[Path]]:
    """Walk tokens from right, collect trailing media tokens, rest is request.

    A token is treated as a file if it exists on disk OR has a recognised
    media extension.  Collection stops at the first token that satisfies
    neither condition.
    """
    files: list[Path] = []
    i = len(tokens) - 1
    while i >= 0:
        tok = tokens[i]
        p = Path(tok)
        if p.exists() or p.suffix.lower() in MEDIA_EXTS:
            files.insert(0, p)
            i -= 1
        else:
            break
    request = ' '.join(tokens[: i + 1])
    return request, files


def _cwd_media_files() -> list[Path]:
    return sorted(
        f for f in Path.cwd().iterdir()
        if f.is_file() and f.suffix.lower() in MEDIA_EXTS
    )


def _has_filesize_target(text: str) -> bool:
    return any(pat.search(text) for pat in FILESIZE_PATTERNS)


def _print_plan(plan: EditPlan) -> None:
    print("EditPlan:")
    for f in dataclasses.fields(plan):
        val = getattr(plan, f.name)
        if val not in (None, False, []):
            print(f"  {f.name}: {val}")


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='ffmpegi',
        description='Natural-language FFmpeg wrapper — no quotes required.',
        epilog=(
            'Examples:\n'
            '  ffmpegi compress for discord clip.mp4\n'
            '  ffmpegi cut from 1:30 to 2:45 and make it 720p intro.mov\n'
            '  ffmpegi merge these into mkv a.mp4 b.mp4 c.mp4\n'
            '  ffmpegi rip the audio as wav speech.mkv'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument('-o', '--output', metavar='PATH', help='Explicit output path')
    p.add_argument('-n', '--dry-run', action='store_true', dest='dry_run',
                   help='Print the FFmpeg command without executing')
    p.add_argument('--explain', action='store_true',
                   help='Print the parsed EditPlan before running')
    p.add_argument('-v', '--verbose', action='store_true',
                   help='Show parser internals and full FFmpeg stderr')
    p.add_argument('tokens', nargs='*', metavar='WORD|FILE',
                   help='Request text words and/or input file paths (mixed freely)')
    return p


def main(argv: list[str] | None = None) -> int:
    arg_parser = _build_arg_parser()
    args = arg_parser.parse_args(argv)

    request, input_files = split_request_and_files(args.tokens)

    if not request.strip():
        arg_parser.print_help()
        return 1

    # CWD fallback when no files appear at end of argv
    if not input_files:
        cwd = _cwd_media_files()
        if len(cwd) == 1:
            input_files = cwd
        else:
            msg = (
                "Multiple media files in the current directory — "
                "pass the one you want as the last argument."
                if cwd else
                "No input file specified — pass one as the last argument."
            )
            print(f"Error: {msg}", file=sys.stderr)
            return 1

    # Verify every collected file exists
    for f in input_files:
        if not f.exists():
            print(f"File not found: {f}", file=sys.stderr)
            return 1

    # Verify ffmpeg + ffprobe are on PATH
    try:
        check_ffmpeg()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    # Probe duration when a filesize target is present (needed for bitrate calc
    # and for progress percentage display)
    video_duration: float | None = None
    if _has_filesize_target(request) and input_files:
        try:
            video_duration = get_video_duration(input_files[0])
        except Exception:
            pass  # builder.py will call ffprobe internally as fallback

    # Parse natural-language request
    result = parse(request, files=input_files, video_duration=video_duration)
    if isinstance(result, ClarificationError):
        print(f"Error: {result.reason}", file=sys.stderr)
        if result.code:
            print(f"Code:  {result.code}", file=sys.stderr)
        if result.options:
            for opt in result.options:
                print(f"  • {opt}", file=sys.stderr)
        return 1

    plan: EditPlan = result

    if args.explain:
        _print_plan(plan)

    # Derive output path
    if args.output:
        output_path = Path(args.output)
    else:
        ref = input_files[0]
        output_path = derive_output_path(plan, ref)

    # Build ffmpeg argv
    ffmpeg_args = build_ffmpeg_args(plan, output_path, video_duration=video_duration)

    # Always show the command
    print(' '.join(shlex.quote(str(a)) for a in ffmpeg_args))

    if args.dry_run:
        return 0

    # Execute
    try:
        return run_ffmpeg(ffmpeg_args, video_duration=video_duration, verbose=args.verbose)
    except PermissionError:
        print(f"Permission denied writing to: {output_path}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
