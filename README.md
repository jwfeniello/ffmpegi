<div align="center">

# FFMPEGI

### FFMPEG Intelligent
<sub><i>or ffmpeg idiot in my case</i></sub>

<a href="#readme-top">
  <img alt="typing" src="https://readme-typing-svg.demolab.com/?lines=ffmpegi+convert+this+to+mp4+video.avi;ffmpegi+compress+for+discord+big_video.mp4;ffmpegi+rip+the+audio+as+wav+speech.mkv;ffmpegi+compress+to+under+25+mb+video.mp4;ffmpegi+cut+from+1:30+to+2:45+clip.mov;ffmpegi+download+in+1080p+https://youtu.be/abc;ffmpegi+rip+the+audio+as+mp3+https://youtu.be/xyz;ffmpegi+download+and+compress+for+discord+URL;ffmpegi+merge+these+into+mkv+clip1.mp4+clip2.mp4;ffmpegi+make+this+720p+movie.mkv;ffmpegi+extract+audio+to+mp3+podcast.mp4;ffmpegi+resize+this+to+480p+anime.mp4&font=Fira+Code&size=20&duration=2600&pause=600&color=A855F7&center=true&width=720&height=46&vCenter=true"/>
</a>

</div>

<br/><br/>

A command-line tool that turns natural-language edit and download requests into FFmpeg + yt-dlp commands and runs them.

```bash
ffmpegi convert this to mp4 video.avi
ffmpegi cut from 1:30 to 2:45 and make it 720p clip.mov
ffmpegi compress for discord big_video.mp4
ffmpegi rip the audio as wav speech.mkv
ffmpegi compress to under 25 mb video.mp4
ffmpegi download in 1080p https://youtube.com/watch?v=abc
ffmpegi download and compress for discord https://youtu.be/xyz
```

The tool figures out which arguments are the request, which are file paths, and which are URLs.

## Requirements

- Windows 10 or later
- [FFmpeg](https://www.gyan.dev/ffmpeg/builds/) on your PATH
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) on your PATH (only needed for URL downloads)
- Python 3.10+ (only if building from source)

## Install

Grab `ffmpegi.exe` from the Releases page and drop it anywhere on your PATH. A folder like `C:\Tools` works fine, add it to your system PATH via Environment Variables.

For URL downloading, install yt-dlp separately:

```bash
pip install yt-dlp
```

Verify:

```bash
ffmpegi --help
```

## What it does

Six edit operations plus URL downloading, all combinable in one request:

| Task | Example |
|------|---------|
| Trim | `cut from 1:30 to 2:45` |
| Convert | `convert to mp4` |
| Resize | `make it 720p` |
| Compress | `compress for discord` or `under 25 mb` |
| Extract audio | `rip the audio as wav` |
| Merge | `merge these into mkv clip1.mp4 clip2.mp4` |
| Download | `download in 1080p URL` |

Multi-intent works: `cut from 0:30 to 1:00 and make it 480p and compress for discord`.

Download + edit in one command: `download in 1080p and compress for discord URL` runs yt-dlp then ffmpeg back-to-back.

Presets: `discord`, `youtube`, `mobile`, `twitter`, `instagram`, `whatsapp`, `telegram`, `email`.

Filesize targets compute the bitrate from input duration: `compress to under 10 mb` does the math.

## Downloading from URLs

Drop a URL anywhere in the command and ffmpegi switches to download mode. Works with anything yt-dlp supports (YouTube, Twitch, Twitter, Vimeo, Reddit, and ~1000 others).

```bash
ffmpegi download in 720p https://youtube.com/watch?v=abc
ffmpegi rip the audio as mp3 https://youtu.be/xyz
ffmpegi grab the best quality https://youtube.com/watch?v=abc
ffmpegi download with english subs https://youtube.com/watch?v=abc
ffmpegi download from 0:30 to 1:00 of https://youtu.be/xyz
```

Combine with edit operations and ffmpegi runs both tools in sequence:

```bash
ffmpegi download in 1080p and compress for discord https://youtu.be/abc
ffmpegi grab the audio as wav and trim from 0:00 to 0:30 https://youtu.be/abc
```

Time ranges on URLs use yt-dlp's section download (faster, smaller, only grabs what you asked for).

## Flags

| Flag | What it does |
|------|--------------|
| `-o PATH` | Explicit output path (otherwise auto-derived) |
| `-n`, `--dry-run` | Print the command(s) without running |
| `--explain` | Print the parsed plan before running |
| `-v`, `--verbose` | Show commands, parser internals, and full output |

## Build from source

```bash
git clone https://github.com/YOUR_USERNAME/ffmpegi
cd ffmpegi
pip install -r requirements.txt
pip install pyinstaller
```

Run from source:

```bash
python src/cli.py convert to mp4 video.avi
```

Build the exe:

```bash
pyinstaller --onefile --name ffmpegi --add-data "vocabulary.py;." --add-data "src;src" --collect-all word2number --collect-all rapidfuzz --hidden-import shlex --paths src src/main.py
```

The exe lands in `dist\ffmpegi.exe`. Copy it onto your PATH.

## Tests

```bash
python -m pytest tests/ -q
```

317 tests covering the parser, CLI, output path derivation, FFmpeg argument building, and yt-dlp integration.

## How it works

1. Normalize, slang, abbreviations, hedge words, sequencers (1000+ vocabulary entries)
2. Parse, span masking, sequencer splitting, fuzzy verb matching with rapidfuzz
3. Disambiguate, resolve "from X to Y" vs "for N seconds", multi-intent merging, conflict detection
4. Compute, bitrate math for filesize targets
5. Build, deterministic EditPlan to FFmpeg or yt-dlp argv
6. Execute, subprocess, stream stderr, parse `time=` for progress, hand off downloaded paths to ffmpeg if requested

The parser is pure rule-based and deterministic. Same input always produces the same output.

## Not supported <sub>yet</sub>

Subtitle burn-in, watermarks, color grading, HDR, stabilization, AI upscaling, denoise, transitions, reverse, speed changes, splitting one video into multiple files, or feeding your dog. The tool returns a clear message instead of trying.

# TLDR for regular(ish) people

basically add the exe to your path or put it in your system32 folder (i know it sounds sus) and then you can just type anywhere in cmd prompt with natural language eg

```bash
ffmpegi convert dis video to mkv stupidvideofile.mp4
```

and poof (◡◕⏖◕)ᑐ🝐 ⠁⭒*.✩.*⭒⠁  
that mf is now stupidvideofile.mkv

or for the YouTube ting

```bash
ffmpegi download in 720p and compress for discord https://youtube.com/watch?v=whatever
```

## License

MIT — see [LICENSE](LICENSE).
