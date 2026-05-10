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
from runner import run_ffmpeg, run_ytdlp             # noqa: E402
from ffmpeg_check import check_ffmpeg, check_ytdlp   # noqa: E402
from vocabulary import FILESIZE_PATTERNS             # noqa: E402
from builder import build_ytdlp_args                 # noqa: E402

VIDEO_EXTS = frozenset({
    '.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv',
    '.wmv', '.m4v', '.mpg', '.mpeg', '.ts',
})
AUDIO_EXTS = frozenset({
    '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.opus',
})
MEDIA_EXTS = VIDEO_EXTS | AUDIO_EXTS


def split_request_and_files(
    tokens: list[str],
) -> tuple[str, list[Path], str | None]:
    """Split tokens into (request_text, input_files, url).

    URL detection: the first token starting with http:// or https:// is
    treated as the download URL and removed before the file-walk.

    File detection: walk remaining tokens from right; collect tokens that
    exist on disk OR have a recognised media extension.  Stop at the first
    token that satisfies neither.  Everything before is the request text.
    """
    url: str | None = None
    non_url_tokens: list[str] = []
    for tok in tokens:
        if tok.startswith(('http://', 'https://')) and url is None:
            url = tok
        else:
            non_url_tokens.append(tok)

    files: list[Path] = []
    i = len(non_url_tokens) - 1
    while i >= 0:
        tok = non_url_tokens[i]
        p = Path(tok)
        if p.exists() or p.suffix.lower() in MEDIA_EXTS:
            files.insert(0, p)
            i -= 1
        else:
            break
    request = ' '.join(non_url_tokens[: i + 1])
    return request, files, url


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


def _has_post_download_ffmpeg_ops(plan: EditPlan) -> bool:
    """Return True if the plan has ffmpeg operations to run after yt-dlp.

    trim_start/trim_end are excluded — they are consumed by yt-dlp
    --download-sections and cleared by build_ytdlp_args().
    """
    return any([
        plan.target_resolution is not None,
        plan.target_format is not None,
        plan.target_filesize_mb is not None,
        plan.target_preset is not None,
        plan.extract_audio,
        plan.audio_format is not None,
    ])


def _fmt_cmd(args: list[str]) -> str:
    return ' '.join(shlex.quote(str(a)) for a in args)


def main(argv: list[str] | None = None) -> int:
    arg_parser = _build_arg_parser()
    args = arg_parser.parse_args(argv)

    # Multiple URLs → error before anything else
    url_count = sum(1 for t in args.tokens if t.startswith(('http://', 'https://')))
    if url_count > 1:
        print("Error: only one URL per command in v1.", file=sys.stderr)
        return 1

    request, input_files, url = split_request_and_files(args.tokens)

    if not request.strip():
        arg_parser.print_help()
        return 1

    # Warn and discard local files when a URL is present
    if url and input_files:
        print(
            f"Warning: ignoring input file(s) {[str(f) for f in input_files]} "
            f"— using URL instead.",
            file=sys.stderr,
        )
        input_files = []

    # CWD fallback (local-file mode only)
    if not url and not input_files:
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

    # Verify every collected local file exists
    for f in input_files:
        if not f.exists():
            print(f"File not found: {f}", file=sys.stderr)
            return 1

    # Check ffmpeg/ffprobe
    try:
        check_ffmpeg()
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 1

    # Check yt-dlp only when needed
    if url:
        try:
            check_ytdlp()
        except SystemExit as exc:
            print(str(exc), file=sys.stderr)
            return 1

    # Probe duration for bitrate computation (local files, filesize target only)
    video_duration: float | None = None
    if not url and _has_filesize_target(request) and input_files:
        try:
            video_duration = get_video_duration(input_files[0])
        except Exception:
            pass

    # Parse
    result = parse(
        request,
        files=input_files if input_files else None,
        video_duration=video_duration,
        url=url,
    )
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

    # ------------------------------------------------------------------ #
    # Download path                                                        #
    # ------------------------------------------------------------------ #
    if plan.download_url:
        output_dir = Path(args.output).parent if args.output else Path.cwd()
        ytdlp_args = build_ytdlp_args(plan, output_dir)

        # Check for remaining ffmpeg ops (trim already consumed by ytdlp_args)
        needs_ffmpeg = _has_post_download_ffmpeg_ops(plan)

        if args.dry_run or args.verbose:
            print(_fmt_cmd(ytdlp_args))
        if needs_ffmpeg and (args.dry_run or args.verbose):
            print("  ↳ then ffmpeg on <downloaded file> (command shown after download)")

        if args.dry_run:
            return 0

        rc, captured = run_ytdlp(ytdlp_args)
        if rc != 0:
            return rc

        # Validate the captured filepath
        lines = [ln.strip() for ln in captured.splitlines() if ln.strip()]
        filepath_str = lines[-1] if lines else ''
        downloaded_path = Path(filepath_str) if filepath_str else None
        if not downloaded_path or not downloaded_path.exists():
            print("Error: couldn't determine downloaded file path.", file=sys.stderr)
            return 1

        if not needs_ffmpeg:
            return 0

        # Wire the downloaded file as the ffmpeg input
        plan.inputs = [downloaded_path]

        # Probe duration for filesize targets on the downloaded file
        if plan.target_filesize_mb is not None:
            try:
                video_duration = get_video_duration(downloaded_path)
            except Exception:
                pass

        if args.output:
            output_path = Path(args.output)
        else:
            output_path = derive_output_path(plan, downloaded_path)

        ffmpeg_args = build_ffmpeg_args(plan, output_path, video_duration=video_duration)
        if args.verbose:
            print(_fmt_cmd(ffmpeg_args))

        try:
            return run_ffmpeg(ffmpeg_args, video_duration=video_duration, verbose=args.verbose)
        except PermissionError:
            print(f"Permission denied writing to: {output_path}", file=sys.stderr)
            return 1

    # ------------------------------------------------------------------ #
    # Local-file ffmpeg path                                               #
    # ------------------------------------------------------------------ #
    if args.output:
        output_path = Path(args.output)
    else:
        ref = input_files[0]
        output_path = derive_output_path(plan, ref)

    ffmpeg_args = build_ffmpeg_args(plan, output_path, video_duration=video_duration)
    if args.dry_run or args.verbose:
        print(_fmt_cmd(ffmpeg_args))

    if args.dry_run:
        return 0

    try:
        return run_ffmpeg(ffmpeg_args, video_duration=video_duration, verbose=args.verbose)
    except PermissionError:
        print(f"Permission denied writing to: {output_path}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
