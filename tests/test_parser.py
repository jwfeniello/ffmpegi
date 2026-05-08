import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from normalize import normalize
from parser import _detect_intent
from compute import compute_video_bitrate
from builder import build_ffmpeg_args
from models import EditPlan


class TestNormalize:
    def test_lowercase(self):
        assert normalize("CUT FROM 1:30") == "cut from 1:30"

    def test_contraction(self):
        assert normalize("i'll trim it") == "i will trim it"

    def test_slang_dis(self):
        # "dis" → "this"
        assert normalize("cut dis from 0:24") == "cut this from 0:24"

    def test_slang_gonna(self):
        assert "going to" in normalize("gonna trim")

    def test_abbreviation_sec(self):
        assert "seconds" in normalize("30 sec")

    def test_abbreviation_min(self):
        assert "minutes" in normalize("2 min")

    def test_strip_filler_can_you(self):
        result = normalize("can you trim from 1:30 to 2:00")
        assert "can you" not in result
        assert "trim" in result

    def test_strip_filler_please(self):
        result = normalize("please convert to mp4")
        assert "please" not in result
        assert "convert" in result

    def test_strip_hedge_like(self):
        result = normalize("under like 25 mb")
        assert "like" not in result
        assert "25" in result

    def test_strip_hedge_try_and(self):
        result = normalize("try and be under 25 mb")
        assert "try and" not in result
        assert "25" in result

    def test_whitespace_normalized(self):
        result = normalize("  cut   from  1:30  ")
        assert "  " not in result
        assert result == result.strip()


from parser import _parse_timestamp, _parse_time_expr
from parser import (
    _extract_resolution, _extract_format, _extract_preset,
    _extract_audio, _extract_filesize,
)
from parser import _find_param_spans, _split_on_sequencers
from parser import _extract_trim
from parser import parse
from models import ClarificationError


class TestTimeParsing:
    def test_mmss(self):
        assert _parse_timestamp("1:30") == 90.0

    def test_hhmmss(self):
        assert _parse_timestamp("1:30:45") == 5445.0

    def test_bare_seconds(self):
        assert _parse_timestamp("90") == 90.0

    def test_bare_seconds_float(self):
        assert _parse_timestamp("1.5") == 1.5

    def test_mmss_decimal(self):
        assert _parse_timestamp("1:30.5") == 90.5

    def test_time_expr_seconds(self):
        assert _parse_time_expr("30 seconds") == 30.0

    def test_time_expr_minutes(self):
        assert _parse_time_expr("2 minutes") == 120.0

    def test_time_expr_hours(self):
        assert _parse_time_expr("1 hours") == 3600.0

    def test_time_expr_short_s(self):
        assert _parse_time_expr("30 s") == 30.0

    def test_time_expr_short_m(self):
        assert _parse_time_expr("2 m") == 120.0

    def test_time_expr_short_min(self):
        assert _parse_time_expr("2 min") == 120.0

    def test_time_expr_word_number(self):
        assert _parse_time_expr("two minutes") == 120.0

    def test_time_expr_word_number_compound(self):
        assert _parse_time_expr("two minutes thirty seconds") == 150.0

    def test_time_expr_timestamp_passthrough(self):
        assert _parse_time_expr("1:30") == 90.0


class TestParamExtraction:
    # Resolution
    def test_resolution_720p_explicit(self):
        assert _extract_resolution("make it 720p") == "720p"

    def test_resolution_1080p_synonym(self):
        assert _extract_resolution("full hd") == "1080p"

    def test_resolution_4k(self):
        assert _extract_resolution("4k resolution") == "2160p"

    def test_resolution_none(self):
        assert _extract_resolution("convert to mp4") is None

    # Format
    def test_format_mp4(self):
        assert _extract_format("convert to mp4") == "mp4"

    def test_format_mkv_alias(self):
        assert _extract_format("save as matroska") == "mkv"

    def test_format_webm(self):
        assert _extract_format("export as webm") == "webm"

    def test_format_none(self):
        assert _extract_format("make it 720p") is None

    # Preset
    def test_preset_discord(self):
        assert _extract_preset("for discord") == "discord"

    def test_preset_twitter(self):
        assert _extract_preset("for twitter") == "twitter"

    def test_preset_youtube(self):
        assert _extract_preset("for youtube") is None  # not in PRESET_TRIGGERS

    def test_preset_none(self):
        assert _extract_preset("make it 720p") is None

    # Audio extraction
    def test_audio_extract_mp3(self):
        flag, fmt = _extract_audio("extract audio as mp3")
        assert flag is True and fmt == "mp3"

    def test_audio_extract_wav(self):
        flag, fmt = _extract_audio("rip audio wav")
        assert flag is True and fmt == "wav"

    def test_audio_no_format(self):
        flag, fmt = _extract_audio("just the audio")
        assert flag is True and fmt is None

    def test_audio_not_present(self):
        flag, fmt = _extract_audio("make it 720p")
        assert flag is False and fmt is None

    # Filesize
    def test_filesize_under_mb(self):
        assert _extract_filesize("under 25 mb") == pytest.approx(25.0)

    def test_filesize_less_than(self):
        assert _extract_filesize("less than 8 mb") == pytest.approx(8.0)

    def test_filesize_megs(self):
        assert _extract_filesize("under 50 megs") == pytest.approx(50.0)

    def test_filesize_none(self):
        assert _extract_filesize("make it 720p") is None


class TestSpanSplit:
    def test_range_span_found(self):
        text = "from 1:30 to 2:45 and make it 720p"
        spans = _find_param_spans(text)
        assert len(spans) >= 1
        # Span should cover "from 1:30 to 2:45"
        range_start = text.index("from")
        range_end = text.index("2:45") + 4
        assert any(s <= range_start and e >= range_end for s, e in spans)

    def test_no_false_split_inside_range(self):
        text = "from 1:30 to 2:45 and make it 720p"
        spans = _find_param_spans(text)
        segs = _split_on_sequencers(text, spans)
        # "and" inside range must NOT split; only the outer "and" splits
        assert len(segs) == 2
        assert any("1:30" in s for s in segs)
        assert any("720p" in s for s in segs)

    def test_split_on_then(self):
        text = "trim to 30 seconds then convert to mp4"
        spans = _find_param_spans(text)
        segs = _split_on_sequencers(text, spans)
        assert len(segs) == 2

    def test_split_and_also(self):
        text = "make it 720p also convert to mkv"
        spans = _find_param_spans(text)
        segs = _split_on_sequencers(text, spans)
        assert len(segs) == 2

    def test_no_sequencer(self):
        text = "cut from 1:30 to 2:45"
        spans = _find_param_spans(text)
        segs = _split_on_sequencers(text, spans)
        assert len(segs) == 1

    def test_filesize_and_not_split(self):
        text = "compress to under 25 mb and make it 720p"
        spans = _find_param_spans(text)
        segs = _split_on_sequencers(text, spans)
        assert len(segs) == 2
        assert any("25" in s for s in segs)
        assert any("720p" in s for s in segs)


class TestVerbDetection:
    def test_trim_cut(self):
        assert _detect_intent("cut from 1:30 to 2:45") == "trim"

    def test_trim_typo(self):
        assert _detect_intent("trmm from 1:30 to 2:00") == "trim"

    def test_trim_snip(self):
        assert _detect_intent("snip from 10 to 30") == "trim"

    def test_convert_explicit(self):
        assert _detect_intent("convert to mp4") == "convert"

    def test_convert_export(self):
        assert _detect_intent("export as mkv") == "convert"

    def test_resize_make_it(self):
        assert _detect_intent("make it 720p") == "resize"

    def test_compress_squeeze(self):
        assert _detect_intent("squeeze it down") == "compress"

    def test_extract_audio(self):
        assert _detect_intent("extract audio as mp3") == "extract_audio"

    def test_merge(self):
        assert _detect_intent("merge these clips") == "merge"

    def test_unknown(self):
        assert _detect_intent("add subtitles") is None

    def test_typo_trim_clip(self):
        # "clipp" should fuzzy-match to "clip" → trim
        assert _detect_intent("clipp the video") == "trim"


class TestTrimExtraction:
    def test_from_to_mmss(self):
        r = _extract_trim("cut from 1:30 to 2:45", None)
        assert r == {'trim_start': 90.0, 'trim_end': 165.0}

    def test_from_to_seconds(self):
        r = _extract_trim("from 0:24 to 30 seconds", None)
        assert r == {'trim_start': 24.0, 'trim_end': 30.0}

    def test_range_dash(self):
        r = _extract_trim("1:00-2:00", None)
        assert r == {'trim_start': 60.0, 'trim_end': 120.0}

    def test_first_n_seconds(self):
        r = _extract_trim("first 30 seconds", None)
        assert r == {'trim_start': 0.0, 'trim_end': 30.0}

    def test_first_n_minutes(self):
        r = _extract_trim("first 2 minutes", None)
        assert r == {'trim_start': 0.0, 'trim_end': 120.0}

    def test_last_n_seconds_with_duration(self):
        r = _extract_trim("last 30 seconds", 180.0)
        assert r == {'trim_start': 150.0, 'trim_end': 180.0}

    def test_last_n_minutes_with_duration(self):
        r = _extract_trim("last 2 minutes", 180.0)
        assert r == {'trim_start': 60.0, 'trim_end': 180.0}

    def test_last_needs_duration(self):
        r = _extract_trim("last 30 seconds", None)
        assert isinstance(r, ClarificationError)
        assert r.code == "need_duration"

    def test_duration_only_for_n_seconds(self):
        r = _extract_trim("keep for 30 seconds", None)
        assert r == {'trim_start': 0.0, 'trim_end': 30.0}

    def test_no_trim(self):
        r = _extract_trim("convert to mp4", None)
        assert r == {}


class TestCompute:
    def test_basic_25mb_60s(self):
        # (25 * 8192 / 60) - 128 ≈ 3285 kbps
        result = compute_video_bitrate(25.0, 60.0)
        assert result == pytest.approx(3285, abs=5)

    def test_8mb_30s(self):
        # (8 * 8192 / 30) - 128 ≈ 2056 kbps
        result = compute_video_bitrate(8.0, 30.0)
        assert result == pytest.approx(2056, abs=5)

    def test_custom_audio_kbps(self):
        result = compute_video_bitrate(25.0, 60.0, audio_kbps=192)
        assert result == pytest.approx(3221, abs=5)

    def test_minimum_clamped_to_50(self):
        # Tiny filesize → result should be at least 50 kbps
        result = compute_video_bitrate(0.1, 60.0)
        assert result >= 50


class TestBuilder:
    def _plan(self, **kwargs) -> EditPlan:
        from models import EditPlan
        return EditPlan(inputs=[Path("in.mp4")], **kwargs)

    def test_trim_only(self):
        args = build_ffmpeg_args(self._plan(trim_start=90.0, trim_end=165.0), Path("out.mp4"))
        assert args[0] == 'ffmpeg'
        assert '-ss' in args
        ss_idx = args.index('-ss')
        assert args[ss_idx + 1] == '90.0'
        assert '-to' in args

    def test_convert_mp4(self):
        args = build_ffmpeg_args(self._plan(target_format="mp4"), Path("out.mp4"))
        assert '-c:v' in args
        assert 'libx264' in args

    def test_convert_webm(self):
        args = build_ffmpeg_args(self._plan(target_format="webm"), Path("out.webm"))
        assert 'libvpx-vp9' in args

    def test_resize_720p(self):
        args = build_ffmpeg_args(self._plan(target_resolution="720p"), Path("out.mp4"))
        assert '-vf' in args
        assert any('scale' in a and '720' in a for a in args)

    def test_extract_audio_mp3(self):
        args = build_ffmpeg_args(self._plan(extract_audio=True, audio_format="mp3"), Path("out.mp3"))
        assert '-vn' in args
        assert 'libmp3lame' in args

    def test_extract_audio_default_mp3(self):
        args = build_ffmpeg_args(self._plan(extract_audio=True, audio_format=None), Path("out.mp3"))
        assert '-vn' in args
        assert 'libmp3lame' in args

    def test_merge_two_files(self):
        from models import EditPlan
        plan = EditPlan(inputs=[Path("a.mp4"), Path("b.mp4")])
        args = build_ffmpeg_args(plan, Path("out.mp4"))
        assert args.count('-i') == 2
        assert '-filter_complex' in args

    def test_compress_with_bitrate(self):
        args = build_ffmpeg_args(
            self._plan(target_filesize_mb=25.0),
            Path("out.mp4"),
            video_duration=60.0,
        )
        assert '-b:v' in args

    def test_output_path_last(self):
        args = build_ffmpeg_args(self._plan(target_format="mp4"), Path("out.mp4"))
        assert args[-1] == 'out.mp4'

    def test_y_flag(self):
        args = build_ffmpeg_args(self._plan(target_format="mp4"), Path("out.mp4"))
        assert '-y' in args

    def test_ss_before_input(self):
        args = build_ffmpeg_args(self._plan(trim_start=30.0, trim_end=60.0), Path("out.mp4"))
        ss_idx = args.index('-ss')
        i_idx = args.index('-i')
        assert ss_idx < i_idx  # -ss must come before -i for fast seek


_F = [Path("test.mp4")]  # default single-file fixture


class TestRequiredCases:
    """The 10 spec-mandated test cases with exact expected EditPlans."""

    def test_01_cut_from_to(self):
        r = parse("cut from 1:30 to 2:45", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(90.0)
        assert r.trim_end == pytest.approx(165.0)

    def test_02_convert_to_mp4(self):
        r = parse("convert to mp4", files=_F)
        assert isinstance(r, EditPlan)
        assert r.target_format == "mp4"

    def test_03_make_it_720p(self):
        r = parse("make it 720p", files=_F)
        assert isinstance(r, EditPlan)
        assert r.target_resolution == "720p"

    def test_04_extract_audio_as_mp3(self):
        r = parse("extract audio as mp3", files=_F)
        assert isinstance(r, EditPlan)
        assert r.extract_audio is True
        assert r.audio_format == "mp3"

    def test_05_compress_for_discord(self):
        r = parse("compress for discord", files=_F)
        assert isinstance(r, EditPlan)
        assert r.target_preset == "discord"

    def test_06_complex_slang_multi_intent(self):
        text = (
            "cut dis from 0:24 to 30 seconds and then make it 720p "
            "and optimize it try and be under like 25 mb"
        )
        r = parse(text, files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(24.0)
        assert r.trim_end == pytest.approx(30.0)
        assert r.target_resolution == "720p"
        assert r.target_filesize_mb == pytest.approx(25.0)

    def test_07_first_30_seconds(self):
        r = parse("first 30 seconds", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(0.0)
        assert r.trim_end == pytest.approx(30.0)

    def test_08_last_2_minutes(self):
        r = parse("last 2 minutes", files=_F, video_duration=180.0)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(60.0)
        assert r.trim_end == pytest.approx(180.0)

    def test_09_multi_intent_trim_convert_resize(self):
        r = parse("trim from 1:30 to 2:45 and convert to mkv and make it 1080p", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(90.0)
        assert r.trim_end == pytest.approx(165.0)
        assert r.target_format == "mkv"
        assert r.target_resolution == "1080p"

    def test_10_make_it_smaller_clarification(self):
        r = parse("make it smaller", files=_F)
        assert isinstance(r, ClarificationError)
        assert r.options is not None
        assert "smaller resolution" in r.options
        assert "smaller filesize" in r.options


# =============================================================================
# Parametrized batches
# =============================================================================

# --- Trim variations (20) ---
@pytest.mark.parametrize("text,start,end", [
    ("trim from 0:30 to 1:00",               30.0,  60.0),
    ("cut from 0:00 to 0:45",                 0.0,  45.0),
    ("clip 0:10 to 0:50",                    10.0,  50.0),
    ("snip from 2:00 to 3:30",              120.0, 210.0),
    ("extract from 0:05 to 0:15",             5.0,  15.0),
    ("grab 1:00-2:00",                       60.0, 120.0),
    ("keep from 0:20 to 0:40",               20.0,  40.0),
    ("isolate from 0:30 to 1:30",            30.0,  90.0),
    ("between 1:00 and 2:00",                60.0, 120.0),
    ("0:00 through 0:30",                     0.0,  30.0),
    ("from 90 to 120",                       90.0, 120.0),
    ("starting at 0:30 ending at 1:00",      30.0,  60.0),
    ("cut from 0 to 45 seconds",              0.0,  45.0),
    ("slice from 10 seconds to 30 seconds",  10.0,  30.0),
    ("section from 1:30 to 2:00",            90.0, 120.0),
    ("first 60 seconds",                      0.0,  60.0),
    ("first 1 minutes",                       0.0,  60.0),
    ("keep for 45 seconds",                   0.0,  45.0),
    ("duration of 30 seconds",                0.0,  30.0),
    ("trim 0:15 to 0:45",                    15.0,  45.0),
])
def test_trim_variations(text, start, end):
    r = parse(text, files=_F)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    assert r.trim_start == pytest.approx(start, abs=0.1), text
    assert r.trim_end == pytest.approx(end, abs=0.1), text


# --- Convert variations (15) ---
@pytest.mark.parametrize("text,expected_fmt", [
    ("convert to mkv",         "mkv"),
    ("save as mov",            "mov"),
    ("export as webm",         "webm"),
    ("turn into avi",          "avi"),
    ("make it a mp4",          "mp4"),
    ("transcode to mkv",       "mkv"),
    ("change to webm",         "webm"),
    ("output to mp4",          "mp4"),
    ("render as mov",          "mov"),
    ("reformat to mkv",        "mkv"),
    ("encode as mp4",          "mp4"),
    ("remux to mkv",           "mkv"),
    ("switch to webm",         "webm"),
    ("bounce to mp4",          "mp4"),
    ("format as mov",          "mov"),
])
def test_convert_variations(text, expected_fmt):
    r = parse(text, files=_F)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    assert r.target_format == expected_fmt, text


# --- Resize variations (15) ---
@pytest.mark.parametrize("text,expected_res", [
    ("make it 1080p",          "1080p"),
    ("scale to 480p",          "480p"),
    ("resize to 360p",         "360p"),
    ("downscale to 720p",      "720p"),
    ("change resolution to 1080p", "1080p"),
    ("set resolution to 720p", "720p"),
    ("make it full hd",        "1080p"),
    ("drop it to 480p",        "480p"),
    ("bump up to 1080p",       "1080p"),
    ("scale down to 480p",     "480p"),
    ("scale up to 1440p",      "1440p"),
    ("make it 4k",             "2160p"),
    ("make it hd",             "720p"),
    ("change size to 360p",    "360p"),
    ("force resolution to 240p", "240p"),
])
def test_resize_variations(text, expected_res):
    r = parse(text, files=_F)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    assert r.target_resolution == expected_res, text


# --- Compress variations (15) ---
@pytest.mark.parametrize("text,preset,filesize", [
    ("compress for discord",          "discord",  None),
    ("optimize for twitter",          "twitter",  None),
    ("shrink for instagram",          "instagram", None),
    ("compress for email",            "email",    None),
    ("squeeze for whatsapp",          "whatsapp", None),
    ("compress for tiktok",           "tiktok",   None),
    ("under 8 mb",                    None,       8.0),
    ("less than 50 mb",               None,       50.0),
    ("max 100 mb",                    None,       100.0),
    ("keep it under 25 mb",          None,       25.0),
    ("no bigger than 10 mb",         None,       10.0),
    ("compress to under 20 mb",      None,       20.0),
    ("shrink to 15 mb",              None,       15.0),
    ("for discord nitro",            "discord_nitro", None),
    ("compress it",                  "youtube",  None),
])
def test_compress_variations(text, preset, filesize):
    r = parse(text, files=_F)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    if preset is not None:
        assert r.target_preset == preset, text
    if filesize is not None:
        assert r.target_filesize_mb == pytest.approx(filesize, rel=0.01), text


# --- Extract audio variations (10) ---
@pytest.mark.parametrize("text,expected_fmt", [
    ("extract audio as mp3",    "mp3"),
    ("rip audio to wav",        "wav"),
    ("get audio as m4a",        "m4a"),
    ("audio only",              None),
    ("just audio",              None),
    ("strip audio",             None),
    ("pull audio as mp3",       "mp3"),
    ("isolate audio",           None),
    ("save audio as wav",       "wav"),
    ("export audio as flac",    "flac"),
])
def test_extract_audio_variations(text, expected_fmt):
    r = parse(text, files=_F)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    assert r.extract_audio is True, text
    assert r.audio_format == expected_fmt, text


# --- Merge variations (10) ---
@pytest.mark.parametrize("text", [
    "merge these clips",
    "combine these videos",
    "join the files",
    "concatenate these",
    "stitch them together",
    "glue these clips",
    "append the files",
    "fuse these videos",
    "put them together",
    "string these together",
])
def test_merge_variations(text):
    files = [Path("a.mp4"), Path("b.mp4")]
    r = parse(text, files=files)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    assert len(r.inputs) == 2, text


# --- Typo / fuzzy variations (10) ---
@pytest.mark.parametrize("text,expected_type,check", [
    ("trmm from 1:30 to 2:45",          EditPlan,           lambda r: r.trim_start == pytest.approx(90.0)),
    ("convret to mp4",                  EditPlan,           lambda r: r.target_format == "mp4"),
    ("mkae it 720p",                    EditPlan,           lambda r: r.target_resolution == "720p"),
    ("extrct audio as mp3",             EditPlan,           lambda r: r.extract_audio is True),
    ("compres for discord",             EditPlan,           lambda r: r.target_preset == "discord"),
    ("clipp from 0:30 to 1:00",        EditPlan,           lambda r: r.trim_start == pytest.approx(30.0)),
    ("resiize to 1080p",               EditPlan,           lambda r: r.target_resolution == "1080p"),
    ("snipp from 1:00 to 2:00",        EditPlan,           lambda r: r.trim_start == pytest.approx(60.0)),
    ("trancscode to mkv",              EditPlan,           lambda r: r.target_format == "mkv"),
    ("scrunch it for discord",         EditPlan,           lambda r: r.target_preset == "discord"),
])
def test_typo_variations(text, expected_type, check):
    r = parse(text, files=_F)
    assert isinstance(r, expected_type), f"Expected {expected_type.__name__}, got {r!r} for {text!r}"
    assert check(r), f"Check failed for {text!r}, got {r!r}"


# --- Number-word variations (5) ---
@pytest.mark.parametrize("text,start,end", [
    ("first thirty seconds",               0.0,  30.0),
    ("first two minutes",                  0.0, 120.0),
    ("keep for forty five seconds",        0.0,  45.0),
    ("trim from 0:00 for one minute",      0.0,  60.0),
    ("cut from 0 to sixty seconds",        0.0,  60.0),
])
def test_number_word_variations(text, start, end):
    r = parse(text, files=_F)
    assert isinstance(r, EditPlan), f"Expected EditPlan, got {r!r} for {text!r}"
    assert r.trim_start == pytest.approx(start, abs=0.5), text
    assert r.trim_end == pytest.approx(end, abs=0.5), text


# --- Ambiguous / ClarificationError cases (5) ---
@pytest.mark.parametrize("text,expected_code", [
    ("make it smaller",                    None),
    ("last 30 seconds",                   "need_duration"),
    ("add subtitles",                     "unrecognized"),
    ("",                                  "unrecognized"),
    ("merge these",                       "no_input_file"),
])
def test_ambiguous_cases(text, expected_code):
    files_arg = _F if text != "merge these" else None
    r = parse(text, files=files_arg)
    assert isinstance(r, ClarificationError), f"Expected ClarificationError, got {r!r} for {text!r}"
    if expected_code is not None:
        assert r.code == expected_code, f"Expected code {expected_code!r}, got {r.code!r} for {text!r}"


# --- Fix: preset word-boundary detection ---
class TestPresetWordBoundary:
    def test_discord_matches(self):
        from parser import _extract_preset
        assert _extract_preset("for discord") == "discord"

    def test_insta_matches_instagram(self):
        from parser import _extract_preset
        assert _extract_preset("for insta") == "instagram"

    def test_insta_substring_no_match(self):
        # "insta" is a substring of "instantly" — word boundary must prevent false match
        from parser import _extract_preset
        assert _extract_preset("do it instantly") is None

    def test_youtube_no_match(self):
        # "youtube" is not in PRESET_TRIGGERS
        from parser import _extract_preset
        assert _extract_preset("upload to youtube") is None

    def test_tube_no_match(self):
        # "tube" should not match any trigger
        from parser import _extract_preset
        assert _extract_preset("tube") is None


# --- Fix: "from X for Y" start + duration semantics ---
class TestFromForSemantics:
    def test_from_for_seconds(self):
        r = parse("trim from 1:30 for 30 seconds", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(90.0)
        assert r.trim_end == pytest.approx(120.0)

    def test_from_for_minute(self):
        r = parse("clip from 0:30 for 1 minute", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(30.0)
        assert r.trim_end == pytest.approx(90.0)

    def test_from_for_seconds_variant(self):
        r = parse("cut from 2:00 for 45 seconds", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(120.0)
        assert r.trim_end == pytest.approx(165.0)


# --- Fix 1: subtitle extraction guard ---
class TestSubtitleGuard:
    def test_subtitle_file_clarifies(self):
        r = parse("extract the subtitle file", files=_F)
        assert isinstance(r, ClarificationError)
        assert r.code == "subtitle_extraction_unsupported"

    def test_srt_clarifies(self):
        r = parse("extract the srt", files=_F)
        assert isinstance(r, ClarificationError)
        assert r.code == "subtitle_extraction_unsupported"

    def test_captions_clarifies(self):
        r = parse("rip the captions", files=_F)
        assert isinstance(r, ClarificationError)
        assert r.code == "subtitle_extraction_unsupported"

    def test_extract_audio_still_works(self):
        r = parse("extract the audio", files=_F)
        assert isinstance(r, EditPlan)
        assert r.extract_audio is True

    def test_rip_audio_wav_still_works(self):
        r = parse("rip the audio as wav", files=_F)
        assert isinstance(r, EditPlan)
        assert r.extract_audio is True
        assert r.audio_format == "wav"


# --- Fix 2: multi-range trim clarification ---
class TestMultiRangeTrim:
    def test_two_dash_ranges_clarifies(self):
        r = parse("cut at 1:24-1:53 1:57-2:10", files=_F)
        assert isinstance(r, ClarificationError)
        assert r.code == "multi_range_unsupported"

    def test_two_ranges_space_separated_clarifies(self):
        r = parse("trim 1:00-1:30 2:00-2:30", files=_F)
        assert isinstance(r, ClarificationError)
        assert r.code == "multi_range_unsupported"

    def test_single_range_still_works(self):
        r = parse("cut from 1:24 to 1:53", files=_F)
        assert isinstance(r, EditPlan)
        assert r.trim_start == pytest.approx(84.0)
        assert r.trim_end == pytest.approx(113.0)
