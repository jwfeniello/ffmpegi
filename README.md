# FFMPEGI

**FFMPEG Intelligent**

<sub>or ffmpeg idiot in my case</sub>

A command-line tool that turns natural-language video edit requests into FFmpeg commands and runs them.

```
ffmpegi convert this to mp4 video.avi
ffmpegi cut from 1:30 to 2:45 and make it 720p clip.mov
ffmpegi compress for discord big_video.mp4
ffmpegi rip the audio as wav speech.mkv
ffmpegi compress to under 25 mb video.mp4
```

No quotes required. The tool figures out which arguments are the request and which are file paths.

## Requirements

- Windows 10 or later
- [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) on your PATH
- Python 3.10+ (only if building from source)

## Install

Grab `ffmpegi.exe` from the Releases page and drop it anywhere on your PATH. A folder like `C:\Tools` works fine — add it to your system PATH via Environment Variables.

Verify:

```
ffmpegi --help
```

## What it does

Six operations, combinable in one request:

| Task | Example |
|------|---------|
| Trim | `cut from 1:30 to 2:45` |
| Convert | `convert to mp4` |
| Resize | `make it 720p` |
| Compress | `compress for discord` or `under 25 mb` |
| Extract audio | `rip the audio as wav` |
| Merge | `merge these into mkv clip1.mp4 clip2.mp4` |

Multi-intent works: `cut from 0:30 to 1:00 and make it 480p and compress for discord`.

Presets: `discord`, `youtube`, `mobile`, `twitter`, `instagram`, `whatsapp`, `telegram`, `email`.

Filesize targets compute the bitrate from input duration: `compress to under 10 mb` does the math.

## Flags

| Flag | What it does |
|------|--------------|
| `-o PATH` | Explicit output path (otherwise auto-derived) |
| `-n`, `--dry-run` | Print the FFmpeg command without running it |
| `--explain` | Print the parsed plan before running |
| `-v`, `--verbose` | Show parser internals and full FFmpeg output |

## Build from source

```
git clone https://github.com/YOUR_USERNAME/ffmpegi
cd ffmpegi
pip install -r requirements.txt
pip install pyinstaller
```

Run from source:

```
python src/cli.py convert to mp4 video.avi
```

Build the exe:

```
pyinstaller --onefile --name ffmpegi --add-data "vocabulary.py;." --add-data "src;src" --collect-all word2number --collect-all rapidfuzz --hidden-import shlex --paths src src/main.py
```

The exe lands in `dist\ffmpegi.exe`. Copy it onto your PATH.

## Tests

```
python -m pytest tests/ -q
```

257 tests covering the parser, CLI, output path derivation, and FFmpeg argument building.

## How it works

1. Normalize — slang, abbreviations, hedge words, sequencers (1000+ vocabulary entries)
2. Parse — span masking, sequencer splitting, fuzzy verb matching with rapidfuzz
3. Disambiguate — resolve "from X to Y" vs "for N seconds", multi-intent merging, conflict detection
4. Compute — bitrate math for filesize targets
5. Build — deterministic EditPlan to FFmpeg argv
6. Execute — subprocess, stream stderr, parse `time=` for progress

The parser is pure rule-based and deterministic. Same input always produces the same output.

## Not supported

Subtitle work, watermarks, color grading, HDR, stabilization, AI upscaling, denoise, transitions, reverse, speed changes, splitting one video into multiple files. The tool returns a clear message instead of trying.

## License

MIT
