from __future__ import annotations
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from vocabulary import (
    TRIM_VERBS, CONVERT_VERBS, RESIZE_VERBS, COMPRESS_VERBS,
    EXTRACT_AUDIO_VERBS, MERGE_VERBS, DOWNLOAD_INTENT_VERBS,
    RESOLUTION_SYNONYMS, FORMAT_ALIASES, PRESET_TRIGGERS,
    RANGE_PATTERNS, DURATION_PATTERNS, RELATIVE_TIME_PATTERNS,
    FILESIZE_PATTERNS, UNIT_TO_BYTES, SEQUENCERS, NUMBER_WORDS,
    QUALITY_KEYWORDS, SUB_KEYWORDS, SUB_AUTO_KEYWORDS,
    PLAYLIST_KEYWORDS, THUMBNAIL_KEYWORDS, METADATA_KEYWORDS,
    SUB_LANG_RE, SUB_LANG_MAP, CUT_AT_PATTERN,
    RECORD_VERBS, CROP_VERBS,
    DIMENSIONS_PATTERN, DIMENSIONS_BY_PATTERN,
    SCALE_PCT_PATTERN, SCALE_MULT_PATTERN, SCALE_WORDS,
    CROP_ASPECT_MAP, CROP_POSITION_MAP,
)
from models import EditPlan, ClarificationError
from normalize import normalize

try:
    from word2number import w2n as _w2n
    _HAS_W2N = True
except ImportError:
    _HAS_W2N = False


# ---------------------------------------------------------------------------
# Time parsing
# ---------------------------------------------------------------------------

def _parse_timestamp(s: str) -> float:
    """Parse 'MM:SS', 'HH:MM:SS', 'MM:SS.mmm', or bare seconds string."""
    s = s.strip()
    if ':' in s:
        parts = s.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(s)


_UNIT_TO_SECS: dict[str, float] = {
    's': 1, 'sec': 1, 'secs': 1, 'second': 1, 'seconds': 1,
    'm': 60, 'min': 60, 'mins': 60, 'minute': 60, 'minutes': 60,
    'h': 3600, 'hr': 3600, 'hrs': 3600, 'hour': 3600, 'hours': 3600,
}

_TIME_EXPR_PATTERN = re.compile(
    r'(?P<n>[0-9.]+)\s*(?P<unit>s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours)',
    re.IGNORECASE,
)

_WORD_TIME_PATTERN = re.compile(
    r'(?P<n_words>[a-z][a-z\s-]+?)\s+(?P<unit>seconds?|minutes?|hours?)',
    re.IGNORECASE,
)


def _parse_time_expr(s: str) -> float:
    """Parse a time expression that may include unit words or word-numbers.

    Examples: '30 seconds', '2 minutes', 'two minutes thirty seconds', '1:30'
    """
    s = s.strip()

    # Timestamp shortcut
    if re.match(r'^\d+:\d', s):
        return _parse_timestamp(s)

    total = 0.0
    found_any = False

    # Numeric unit matches: "30 seconds", "2 min"
    for m in _TIME_EXPR_PATTERN.finditer(s):
        unit = m.group('unit').lower()
        total += float(m.group('n')) * _UNIT_TO_SECS.get(unit, 1)
        found_any = True

    if found_any:
        return total

    # Word-number unit matches: "two minutes thirty seconds"
    for m in _WORD_TIME_PATTERN.finditer(s):
        n_words = m.group('n_words').strip()
        unit = m.group('unit').lower().rstrip('s')  # normalise plural
        multiplier = {'second': 1, 'minute': 60, 'hour': 3600}.get(unit, 1)
        n: float | None = None
        if _HAS_W2N:
            try:
                n = float(_w2n.word_to_num(n_words))
            except Exception:
                pass
        if n is None:
            n = float(NUMBER_WORDS.get(n_words.lower(), 0) or 0)
        total += n * multiplier
        found_any = True

    if found_any:
        return total

    # Bare number fallback
    try:
        return float(s)
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Parameter extraction helpers
# ---------------------------------------------------------------------------

def _extract_resolution(text: str) -> str | None:
    """Return canonical resolution string ('720p', '1080p', etc.) or None."""
    text_lower = text.lower()
    # Build a flat list of (synonym, canonical) sorted by synonym length descending
    # so longer (more specific) synonyms are matched before shorter ones.
    candidates: list[tuple[str, str]] = []
    for canonical, synonyms in RESOLUTION_SYNONYMS.items():
        for syn in synonyms:
            candidates.append((syn.lower(), canonical))
    candidates.sort(key=lambda x: len(x[0]), reverse=True)
    for syn, canonical in candidates:
        if re.search(r'\b' + re.escape(syn) + r'\b', text_lower):
            return canonical
    return None


def _extract_format(text: str) -> str | None:
    """Return canonical format string ('mp4', 'mkv', etc.) or None."""
    text_lower = text.lower()
    for canonical, aliases in FORMAT_ALIASES.items():
        for alias in aliases:
            if re.search(r'\b' + re.escape(alias.lower()) + r'\b', text_lower):
                return canonical
    return None


def _extract_preset(text: str) -> str | None:
    """Return preset key ('discord', 'twitter', etc.) or None."""
    text_lower = text.lower()
    for preset, triggers in PRESET_TRIGGERS.items():
        for trigger in triggers:
            if re.search(r'\b' + re.escape(trigger.lower()) + r'\b', text_lower):
                return preset
    return None


# Audio format keys that are audio-only (used when extracting audio)
_AUDIO_FORMATS = {'mp3', 'wav', 'm4a', 'aac', 'flac', 'ogg', 'opus'}

_SUBTITLE_KEYWORDS = re.compile(
    r'\b(?:subtitle|subtitles|srt|captions?|cc|vtt)\b', re.IGNORECASE
)

# Extract-like verbs used to detect subtitle-extraction attempts independently of
# the rapidfuzz EXTRACT_AUDIO_VERBS threshold (which is audio-specific and may score low).
_EXTRACT_VERB_RE = re.compile(
    r'\b(?:extract|rip|pull|get|grab|save|export|strip|isolate)\b', re.IGNORECASE
)


def _extract_audio(text: str) -> tuple[bool, str | None] | ClarificationError:
    """Return (extract_audio, audio_format_or_None), or ClarificationError for subtitle requests."""
    from rapidfuzz import process, fuzz
    result = process.extractOne(text, EXTRACT_AUDIO_VERBS, scorer=fuzz.partial_ratio)
    if not result or result[1] < 80:
        return False, None
    if _SUBTITLE_KEYWORDS.search(text):
        return ClarificationError(
            reason="Subtitle extraction isn't supported in this version.",
            code='subtitle_extraction_unsupported',
        )
    fmt = _extract_format(text)
    if fmt not in _AUDIO_FORMATS:
        fmt = None
    return True, fmt


def _extract_filesize(text: str) -> float | None:
    """Return filesize target in MB, or None."""
    for pat in FILESIZE_PATTERNS:
        m = pat.search(text)
        if m:
            n = float(m.group('n'))
            unit = m.group('unit').lower().strip()
            bytes_per_unit = UNIT_TO_BYTES.get(unit)
            if bytes_per_unit is None:
                # Try partial match against UNIT_TO_BYTES keys
                for key in sorted(UNIT_TO_BYTES, key=len, reverse=True):
                    if unit.startswith(key) or key.startswith(unit):
                        bytes_per_unit = UNIT_TO_BYTES[key]
                        break
            if bytes_per_unit is None:
                continue
            return (n * bytes_per_unit) / (1024 ** 2)
    return None


def _extract_resize(text: str) -> dict:
    """Return any of {target_width, target_height, target_scale_pct} found in text."""
    fields: dict = {}

    # WxH or W by H
    for pat in (DIMENSIONS_PATTERN, DIMENSIONS_BY_PATTERN):
        m = pat.search(text)
        if m:
            fields['target_width'] = int(m.group('w'))
            fields['target_height'] = int(m.group('h'))
            return fields

    # Percentage
    m = SCALE_PCT_PATTERN.search(text)
    if m:
        fields['target_scale_pct'] = float(m.group('pct'))
        return fields

    # Multiplier (e.g. 2x, 0.5x)
    m = SCALE_MULT_PATTERN.search(text)
    if m:
        fields['target_scale_pct'] = float(m.group('mult')) * 100.0
        return fields

    # Word-based (half, double, …)
    for word, pct in SCALE_WORDS.items():
        if re.search(r'\b' + word + r'\b', text, re.IGNORECASE):
            fields['target_scale_pct'] = pct
            return fields

    return fields


_CROP_VERB_RE = re.compile(
    r'\b(?:crop|crops|cropped|cropping|crop\s+to|crop\s+out|trim\s+frame|cut\s+frame'
    r'|remove\s+black\s+bars?|letterbox\s+crop|zoom\s+crop)\b',
    re.IGNORECASE,
)


def _extract_crop(text: str) -> dict:
    """Return crop_* fields found in text, or empty dict.

    Aspect ratios are always treated as crop targets.
    WxH dimensions only become a crop when an explicit crop verb is present;
    otherwise they are resize targets handled by _extract_resize.
    """
    text_l = text.lower()

    # Aspect ratio — always implies spatial crop (not a resize)
    for phrase, canonical in sorted(CROP_ASPECT_MAP.items(), key=lambda x: -len(x[0])):
        if phrase in text_l:
            return {'crop_aspect': canonical}

    # WxH — only crop when "crop" verb is explicitly present
    if _CROP_VERB_RE.search(text):
        m = DIMENSIONS_PATTERN.search(text)
        if m:
            result: dict = {'crop_w': int(m.group('w')), 'crop_h': int(m.group('h'))}
            for phrase, (px, py) in sorted(CROP_POSITION_MAP.items(), key=lambda x: -len(x[0])):
                if phrase in text_l:
                    if px is not None:
                        result['crop_x'] = px
                    if py is not None:
                        result['crop_y'] = py
                    break
            return result

    return {}


# ---------------------------------------------------------------------------
# Span masking and sequencer splitting
# ---------------------------------------------------------------------------

def _find_param_spans(text: str) -> list[tuple[int, int]]:
    """Return (start, end) spans of all pattern matches in text.

    Used to prevent sequencer splitting inside parameter expressions
    like 'from 1:30 to 2:45' or 'under 25 mb'.
    """
    spans: list[tuple[int, int]] = []
    all_patterns = list(RANGE_PATTERNS) + list(DURATION_PATTERNS) + list(FILESIZE_PATTERNS)
    for pat in all_patterns:
        for m in pat.finditer(text):
            spans.append((m.start(), m.end()))
    for rtp in RELATIVE_TIME_PATTERNS:
        for m in rtp['pattern'].finditer(text):
            spans.append((m.start(), m.end()))
    return spans


def _in_any_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(s <= pos < e for s, e in spans)


def _split_on_sequencers(text: str, param_spans: list[tuple[int, int]]) -> list[str]:
    """Split text on SEQUENCERS that do not fall inside a param span."""
    sorted_seqs = sorted(SEQUENCERS, key=len, reverse=True)
    seq_re = re.compile(
        r'\b(?:' + '|'.join(re.escape(s) for s in sorted_seqs) + r')\b',
        re.IGNORECASE,
    )
    split_points: list[tuple[int, int]] = []
    for m in seq_re.finditer(text):
        if not _in_any_span(m.start(), param_spans):
            split_points.append((m.start(), m.end()))

    if not split_points:
        return [text.strip()] if text.strip() else []

    segments: list[str] = []
    prev = 0
    for start, end in split_points:
        seg = text[prev:start].strip()
        if seg:
            segments.append(seg)
        prev = end
    tail = text[prev:].strip()
    if tail:
        segments.append(tail)
    return segments if segments else [text.strip()]


# ---------------------------------------------------------------------------
# Verb detection
# ---------------------------------------------------------------------------

_INTENT_VERB_LISTS: list[tuple[str, list[str]]] = [
    ('trim',          list(TRIM_VERBS)),
    ('convert',       list(CONVERT_VERBS)),
    ('resize',        list(RESIZE_VERBS)),
    ('compress',      list(COMPRESS_VERBS)),
    ('extract_audio', list(EXTRACT_AUDIO_VERBS)),
    ('merge',         list(MERGE_VERBS)),
    ('download',      list(DOWNLOAD_INTENT_VERBS)),
    ('record',        list(RECORD_VERBS)),
    ('crop',          list(CROP_VERBS)),
]

_INTENT_PRIORITY = {
    'trim': 6, 'convert': 5, 'resize': 4,
    'compress': 3, 'extract_audio': 2, 'merge': 1, 'download': 7,
    'record': 8, 'crop': 4,
}


def _detect_intent(segment: str) -> str | None:
    """Detect the primary edit intent for a text segment using rapidfuzz.

    Position heuristic: prefer verb matches at the start of the segment
    (first three words) over matches found anywhere. Best-effort — may
    misfire on edge cases where a verb word appears mid-sentence as a noun.
    """
    from rapidfuzz import process, fuzz

    THRESHOLD = 80
    words = segment.split()
    prefix = ' '.join(words[:3])

    best_intent: str | None = None
    best_score = 0
    best_match_len = 0  # length of matched verb string; longer = more specific

    for intent, verbs in _INTENT_VERB_LISTS:
        # Check prefix first for position bonus
        prefix_result = process.extractOne(prefix, verbs, scorer=fuzz.partial_ratio)
        full_result = process.extractOne(segment, verbs, scorer=fuzz.partial_ratio)

        score = 0
        matched_verb = ''
        if prefix_result and prefix_result[1] >= THRESHOLD:
            score = prefix_result[1] + 5  # position bonus
            matched_verb = prefix_result[0]
        elif full_result and full_result[1] >= THRESHOLD:
            score = full_result[1]
            matched_verb = full_result[0]

        # Exact whole-word match bonus: when the matched verb appears as a
        # complete word (not a substring of a different word) in the segment,
        # add +10 to break ties that arise from partial_ratio matching substrings.
        # Example: 'clip' scores 100 against 'glue these clips' via partial_ratio
        # because 'clip' is a substring of 'clips', but it is NOT a whole word.
        if matched_verb and re.search(
            r'\b' + re.escape(matched_verb.lower()) + r'\b',
            segment.lower(),
        ):
            score += 10

        match_len = len(matched_verb)

        # Prefer: higher score, then longer matched verb (more specific), then priority order
        if (
            score > best_score
            or (score == best_score and match_len > best_match_len)
            or (
                score == best_score
                and match_len == best_match_len
                and best_intent is not None
                and _INTENT_PRIORITY.get(intent, 0) > _INTENT_PRIORITY.get(best_intent, 0)
            )
        ):
            best_score = score
            best_intent = intent
            best_match_len = match_len

    return best_intent if best_score >= THRESHOLD else None


# ---------------------------------------------------------------------------
# Word-number → digit replacement for time context
# ---------------------------------------------------------------------------

# Precompile compound (tens + ones) and single-word number patterns used before time units.
_TENS_WORDS = {'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'}
_ONES_WORDS = {
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine',
    'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen',
    'seventeen', 'eighteen', 'nineteen',
}
_TENS_ALT = '|'.join(_TENS_WORDS)
_ONES_ALT = '|'.join(_ONES_WORDS)
_COMPOUND_NUM_RE = re.compile(
    r'\b(?P<tens>' + _TENS_ALT + r')\s+(?P<ones>' + _ONES_ALT + r')\b'
    r'(?=\s+(?:seconds?|minutes?|hours?)\b)',
    re.IGNORECASE,
)
_SINGLE_NUM_KEYS = sorted(
    [k for k in NUMBER_WORDS if NUMBER_WORDS[k] >= 1 and ' ' not in k and k not in ('a', 'an')],
    key=len, reverse=True,
)
_SINGLE_NUM_RE = re.compile(
    r'\b(?P<numword>' + '|'.join(re.escape(k) for k in _SINGLE_NUM_KEYS) + r')\b'
    r'(?=\s+(?:seconds?|minutes?|hours?)\b)',
    re.IGNORECASE,
)


def _replace_word_numbers(text: str) -> str:
    """Replace word-number expressions immediately before time units with digits.

    Examples:
      'first thirty seconds' -> 'first 30 seconds'
      'for forty five seconds' -> 'for 45 seconds'
      'to sixty seconds' -> 'to 60 seconds'
    """
    def _compound_repl(m: re.Match) -> str:
        key = m.group('tens').lower() + '-' + m.group('ones').lower()
        val = NUMBER_WORDS.get(key)
        return str(val) if val else m.group(0)

    def _single_repl(m: re.Match) -> str:
        key = m.group('numword').lower()
        val = NUMBER_WORDS.get(key)
        return str(val) if val else m.group(0)

    text = _COMPOUND_NUM_RE.sub(_compound_repl, text)
    text = _SINGLE_NUM_RE.sub(_single_repl, text)
    return text


# ---------------------------------------------------------------------------
# Trim extraction
# ---------------------------------------------------------------------------

# Matches "from {start} for {duration}" — start + duration semantics.
# Must be checked before RANGE_PATTERNS, which require "to" and would miss this form.
_FROM_FOR_PATTERN = re.compile(
    r'from\s+(?P<start>[0-9:.]+(?:\s*(?:s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))?)'
    r'\s+for\s+(?P<dur>[0-9.]+\s*(?:s|sec|secs|seconds|m|min|mins|minutes|h|hr|hrs|hours))',
    re.IGNORECASE,
)


def _fmt_time(secs: float) -> str:
    """Format seconds as a compact human-readable time string."""
    if secs < 60:
        return f"{int(secs)}s" if secs == int(secs) else f"{secs:.1f}s"
    m_part, s_part = divmod(int(secs), 60)
    h_part, m_part = divmod(m_part, 60)
    if h_part:
        return f"{h_part}:{m_part:02d}:{s_part:02d}"
    return f"{m_part}:{s_part:02d}"


def _extract_trim(
    segment: str, video_duration: float | None
) -> dict[str, float] | ClarificationError:
    """Extract trim_start and trim_end from a text segment.

    Returns a dict with 'trim_start'/'trim_end' keys (possibly empty),
    or ClarificationError when duration is required but not supplied.

    Priority: RANGE_PATTERNS > RELATIVE_TIME_PATTERNS > DURATION_PATTERNS
    """
    # Pre-process: replace word-number expressions before time units
    # e.g. 'first thirty seconds' -> 'first 30 seconds'
    seg = _replace_word_numbers(segment)

    # 0. "from X for Y" — start + duration (checked before RANGE_PATTERNS which need "to")
    m = _FROM_FOR_PATTERN.search(seg)
    if m:
        try:
            start = _parse_time_expr(m.group('start').strip())
            dur = _parse_time_expr(m.group('dur').strip())
            return {'trim_start': start, 'trim_end': start + dur}
        except Exception:
            pass

    # 1. Range patterns: "from X to Y", "X-Y", "between X and Y", etc.
    # Multiple patterns can match the same underlying span (e.g. "keep from X to Y" matches
    # both the keep-pattern and the from-pattern). Deduplicate by span overlap before counting.
    range_matches: list[tuple[float, float]] = []
    seen_spans: list[tuple[int, int]] = []
    for pat in RANGE_PATTERNS:
        for m in pat.finditer(seg):
            # Skip if this match overlaps an already-recorded span (same range, different pattern)
            if any(max(m.start(), s) < min(m.end(), e) for s, e in seen_spans):
                continue
            try:
                s_val = _parse_time_expr(m.group('start').strip())
                e_val = _parse_time_expr(m.group('end').strip())
                range_matches.append((s_val, e_val))
                seen_spans.append((m.start(), m.end()))
            except Exception:
                continue
    if len(range_matches) > 1:
        return ClarificationError(
            reason="Multiple time ranges in one trim aren't supported. Process them as separate clips.",
            code='multi_range_unsupported',
        )
    if len(range_matches) == 1:
        return {'trim_start': range_matches[0][0], 'trim_end': range_matches[0][1]}

    # 2. Relative time patterns: first/last/middle/skip_first/etc.
    for rtp in RELATIVE_TIME_PATTERNS:
        m = rtp['pattern'].search(seg)
        if not m:
            continue
        kind = rtp['kind']
        try:
            n = float(m.group('n'))
        except (ValueError, TypeError):
            n = 0.0  # timestamp form — individual handlers re-parse via _parse_time_expr
        unit = m.group('unit').lower() if 'unit' in m.groupdict() and m.group('unit') else 's'
        dur_secs = n * _UNIT_TO_SECS.get(unit, 1)

        # --- single-point directional cut kinds ---
        if kind in ('cut_before', 'keep_after'):
            n_val = m.group('n')
            t = _parse_time_expr(n_val + ' ' + unit if ':' not in n_val else n_val)
            if video_duration is not None:
                return {'trim_start': t, 'trim_end': video_duration}
            return {'trim_start': t}
        if kind in ('cut_after', 'keep_before'):
            n_val = m.group('n')
            t = _parse_time_expr(n_val + ' ' + unit if ':' not in n_val else n_val)
            return {'trim_start': 0.0, 'trim_end': t}
        if kind == 'cut_first_2':
            if video_duration is not None:
                return {'trim_start': dur_secs, 'trim_end': video_duration}
            return {'trim_start': dur_secs}
        if kind == 'cut_last_2':
            if video_duration is None:
                return ClarificationError(
                    reason="I need the video's duration to resolve that.",
                    code='need_duration',
                )
            return {'trim_start': 0.0, 'trim_end': video_duration - dur_secs}
        # --- end single-point kinds ---
        if kind == 'first':
            return {'trim_start': 0.0, 'trim_end': dur_secs}
        if kind in ('last', 'keep_last'):
            if video_duration is None:
                return ClarificationError(
                    reason=f"I need the video's duration to resolve 'last {n} {unit}'.",
                    code='need_duration',
                )
            return {'trim_start': video_duration - dur_secs, 'trim_end': video_duration}
        if kind in ('skip_first', 'skip_first_2', 'cut_first'):
            if video_duration is None:
                return ClarificationError(
                    reason="I need the video's duration to resolve that.",
                    code='need_duration',
                )
            return {'trim_start': dur_secs, 'trim_end': video_duration}
        if kind in ('skip_last', 'skip_last_2', 'cut_last'):
            if video_duration is None:
                return ClarificationError(
                    reason="I need the video's duration to resolve that.",
                    code='need_duration',
                )
            return {'trim_start': 0.0, 'trim_end': video_duration - dur_secs}
        if kind == 'keep_first':
            return {'trim_start': 0.0, 'trim_end': dur_secs}
        if kind == 'middle':
            if video_duration is None:
                return ClarificationError(
                    reason="I need the video's duration to resolve 'middle N seconds'.",
                    code='need_duration',
                )
            centre = video_duration / 2
            return {'trim_start': centre - dur_secs / 2, 'trim_end': centre + dur_secs / 2}
        if kind in ('after', 'starting_after'):
            n_val = m.group('n')
            t = _parse_time_expr(n_val + ' ' + unit if ':' not in n_val else n_val)
            end = video_duration if video_duration is not None else t + dur_secs
            return {'trim_start': t, 'trim_end': end}
        if kind in ('before', 'up_to'):
            n_val = m.group('n')
            t = _parse_time_expr(n_val + ' ' + unit if ':' not in n_val else n_val)
            return {'trim_start': 0.0, 'trim_end': t}
        if kind == 'past':
            n_val = m.group('n')
            t = _parse_time_expr(n_val)
            end = video_duration if video_duration is not None else t
            return {'trim_start': t, 'trim_end': end}
        if kind == 'everything_except':
            continue

    # 3. Duration patterns: "for 30 seconds" → start=0
    for pat in DURATION_PATTERNS:
        m = pat.search(seg)
        if m:
            try:
                dur = _parse_time_expr(m.group('dur').strip())
                return {'trim_start': 0.0, 'trim_end': dur}
            except Exception:
                continue

    # 4. Ambiguous "cut at X" — ask the user which side to keep.
    m = CUT_AT_PATTERN.search(seg)
    if m:
        t_str = m.group('t')
        unit = m.group('unit') or 's'
        try:
            t = _parse_time_expr(t_str + ' ' + unit if ':' not in t_str else t_str)
            t_disp = _fmt_time(t)
            return ClarificationError(
                reason=f"Cut at {t_disp} — keep the part before or after?",
                options=[f"keep before {t_disp}", f"keep after {t_disp}"],
                code='cut_at_ambiguous',
            )
        except Exception:
            pass

    return {}


# ---------------------------------------------------------------------------
# Segment → field dict
# ---------------------------------------------------------------------------

# Ambiguous requests that need clarification (matched post-normalization)
# "bigger" is only ambiguous when NOT qualified by a filesize expression like "no bigger than N mb"
_AMBIGUOUS_PATTERNS: list[tuple[re.Pattern, ClarificationError]] = [
    (
        re.compile(r'\bsmaller\b', re.IGNORECASE),
        ClarificationError(
            reason="Do you mean smaller resolution or smaller filesize?",
            options=["smaller resolution", "smaller filesize"],
        ),
    ),
    (
        re.compile(r'(?<!no )\bbigger\b(?!\s+than\s+\d)', re.IGNORECASE),
        ClarificationError(
            reason="Do you mean bigger resolution or larger filesize target?",
            options=["bigger resolution", "larger filesize"],
        ),
    ),
]


def _extract_download_params(text: str) -> dict:
    """Extract download-specific fields from full request text when a URL is present.

    Handles quality keywords (best/worst/audio_only), subtitles, playlist,
    thumbnail, and metadata.  Resolution is handled per-segment via the
    'download' intent branch in _parse_segment.
    """
    params: dict = {}
    tl = text.lower()

    # Quality keywords (best/worst/audio_only) — check longest phrases first
    for quality_val, phrases in QUALITY_KEYWORDS.items():
        for phrase in sorted(phrases, key=len, reverse=True):
            if re.search(re.escape(phrase.lower()), tl):
                if quality_val == 'audio_only':
                    params['download_audio_only'] = True
                elif 'download_quality' not in params:
                    params['download_quality'] = quality_val
                break

    # Auto subs (check before regular subs to avoid double-match)
    for kw in SUB_AUTO_KEYWORDS:
        if kw.lower() in tl:
            params['download_subs'] = True
            params['download_sub_auto'] = True
            break

    # Regular subs
    if 'download_subs' not in params:
        for kw in SUB_KEYWORDS:
            if kw.lower() in tl:
                params['download_subs'] = True
                params.setdefault('download_sub_lang', 'en')
                break

    # Explicit sub language: "with english subs", "in japanese subtitles"
    m = SUB_LANG_RE.search(text)
    if m:
        params['download_subs'] = True
        params['download_sub_lang'] = SUB_LANG_MAP.get(m.group(1).lower(), 'en')

    # Playlist
    for kw in PLAYLIST_KEYWORDS.get('force_playlist', []):
        if kw.lower() in tl:
            params['download_playlist'] = True
            break
    if 'download_playlist' not in params:
        for kw in PLAYLIST_KEYWORDS.get('single_only', []):
            if kw.lower() in tl:
                params['download_playlist'] = False
                break

    # Thumbnail
    for kw in THUMBNAIL_KEYWORDS:
        if kw.lower() in tl:
            params['download_thumbnail'] = True
            break

    # Metadata
    for kw in METADATA_KEYWORDS:
        if kw.lower() in tl:
            params['download_metadata'] = True
            break

    return params


def _parse_segment(
    segment: str, intent: str | None, video_duration: float | None
) -> dict | ClarificationError:
    """Convert a single intent segment into a field dict for EditPlan."""
    fields: dict = {}

    # Check ambiguous patterns first
    for pat, err in _AMBIGUOUS_PATTERNS:
        if pat.search(segment):
            return err

    # Subtitle extraction guard — fires regardless of rapidfuzz score, so "rip the captions"
    # (which scores below the audio threshold) is still caught.
    if _SUBTITLE_KEYWORDS.search(segment) and _EXTRACT_VERB_RE.search(segment):
        return ClarificationError(
            reason="Subtitle extraction isn't supported in this version.",
            code='subtitle_extraction_unsupported',
        )

    trim_result = _extract_trim(segment, video_duration)
    if isinstance(trim_result, ClarificationError):
        return trim_result
    fields.update(trim_result)

    # Spatial crop check — aspect ratios and explicit crop+dims override other intents.
    # Only fires when no time-trim was found (so "crop from 0:30 to 1:00" stays as trim).
    if not trim_result:
        crop_fields = _extract_crop(segment)
        if crop_fields:
            fields.update(crop_fields)
            fmt = _extract_format(segment)
            if fmt and fmt not in _AUDIO_FORMATS:
                fields['target_format'] = fmt
            return fields

    res = _extract_resolution(segment)
    if res:
        fields['target_resolution'] = res

    if intent == 'record':
        fields['record_screen'] = True
        # Promote any trim_end → record_duration, then clear it (not a file trim)
        if fields.get('trim_end'):
            fields['record_duration'] = fields.pop('trim_end')
        fields.pop('trim_start', None)
        return fields

    if intent == 'crop':
        crop_fields = _extract_crop(segment)
        # If no explicit dimensions, fall back to aspect ratio from text
        if not crop_fields:
            crop_fields = _extract_crop(segment)
        fields.update(crop_fields)
        return fields

    if intent == 'extract_audio':
        # Intent already established — don't re-run verb detection.
        fields['extract_audio'] = True
        audio_fmt = _extract_format(segment)
        if audio_fmt in _AUDIO_FORMATS:
            fields['audio_format'] = audio_fmt
    elif intent == 'download':
        # Resolution → download_quality so it doesn't conflict with post-download resize
        # Also clear target_resolution set by the early unconditional extraction above.
        res = _extract_resolution(segment)
        if res:
            fields.pop('target_resolution', None)
            fields['download_quality'] = res

        fmt = _extract_format(segment)
        if fmt and fmt not in _AUDIO_FORMATS:
            fields['download_format'] = fmt
        elif fmt and fmt in _AUDIO_FORMATS:
            # Audio format specified → treat as audio-only; normalizer converts to download_audio_only
            fields['extract_audio'] = True
            fields['audio_format'] = fmt

        # Audio extraction in download context (normalizer will convert to download_audio_only)
        audio_result = _extract_audio(segment)
        if isinstance(audio_result, ClarificationError):
            return audio_result
        audio_flag, audio_fmt = audio_result
        if audio_flag:
            fields['extract_audio'] = True
            if audio_fmt:
                fields['audio_format'] = audio_fmt

        # Post-download ffmpeg ops may still be requested in the same segment
        preset = _extract_preset(segment)
        if preset:
            fields['target_preset'] = preset
        filesize = _extract_filesize(segment)
        if filesize is not None:
            fields['target_filesize_mb'] = filesize
    else:
        fmt = _extract_format(segment)
        if fmt:
            fields['target_format'] = fmt

        # Arbitrary resize dimensions / scale percentage
        resize_fields = _extract_resize(segment)
        # Only apply if no preset resolution already set (preset takes priority)
        if resize_fields and not fields.get('target_resolution'):
            fields.update(resize_fields)

        audio_result = _extract_audio(segment)
        if isinstance(audio_result, ClarificationError):
            return audio_result
        audio_flag, audio_fmt = audio_result
        if audio_flag:
            fields['extract_audio'] = True
            if audio_fmt:
                fields['audio_format'] = audio_fmt

    preset = _extract_preset(segment)
    if preset:
        fields['target_preset'] = preset

    filesize = _extract_filesize(segment)
    if filesize is not None:
        fields['target_filesize_mb'] = filesize

    # Bare compress with no filesize and no preset → default to youtube
    if intent == 'compress' and 'target_filesize_mb' not in fields and 'target_preset' not in fields:
        fields['target_preset'] = 'youtube'

    return fields


# ---------------------------------------------------------------------------
# Plan merging
# ---------------------------------------------------------------------------

_MERGEABLE_FIELDS = {
    'trim_start', 'trim_end', 'target_resolution', 'target_format',
    'target_filesize_mb', 'target_preset', 'extract_audio', 'audio_format',
    # download-specific fields (populated from segments or _extract_download_params)
    'download_quality', 'download_format', 'download_audio_only',
    'download_audio_format', 'download_subs', 'download_sub_lang',
    'download_sub_auto', 'download_playlist', 'download_thumbnail',
    'download_metadata',
    # resize
    'target_width', 'target_height', 'target_scale_pct',
    # crop
    'crop_w', 'crop_h', 'crop_x', 'crop_y', 'crop_aspect',
    # record
    'record_screen', 'record_audio_device', 'record_duration',
}


def _merge_plans(plans: list[dict]) -> dict | ClarificationError:
    """Merge multiple segment field dicts into one.

    Returns ClarificationError if any field has conflicting values across segments.
    """
    merged: dict = {}
    for plan in plans:
        for key, value in plan.items():
            if key not in _MERGEABLE_FIELDS:
                continue
            if key in merged:
                if merged[key] != value:
                    return ClarificationError(
                        reason=f"Conflicting values for '{key}': {merged[key]!r} vs {value!r}",
                        code='conflicting_intent',
                    )
            else:
                merged[key] = value
    return merged


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(
    text: str,
    files: list[Path] | None = None,
    video_duration: float | None = None,
    url: str | None = None,
) -> EditPlan | ClarificationError:
    """Convert a natural-language edit request to an EditPlan.

    Args:
        text: User's edit request in natural language.
        files: Input file paths. For single-input tasks, parser uses files[0].
               For merge, uses the full list. If None/empty and task needs
               input, returns ClarificationError(code='no_input_file').
        video_duration: Video length in seconds. Required for relative-time
                        patterns like 'last 2 minutes'.
        url: Download URL (yt-dlp). When set, enables download mode and
             populates download_* fields on the returned EditPlan.

    Returns:
        EditPlan on success, ClarificationError when clarification is needed.
    """
    has_files = bool(files)
    resolved_files: list[Path] = list(files) if files else []

    normalized = normalize(text)

    # Check whole-text ambiguous patterns before splitting
    for pat, err in _AMBIGUOUS_PATTERNS:
        if pat.search(normalized):
            return err

    # Find param spans in normalized text, then split on sequencers
    param_spans = _find_param_spans(normalized)
    segments = _split_on_sequencers(normalized, param_spans)

    if not segments:
        return ClarificationError(
            reason="I couldn't understand that request.",
            code='unrecognized',
        )

    segment_plans: list[dict] = []
    intents: list[str | None] = []

    for seg in segments:
        intent = _detect_intent(seg)
        intents.append(intent)
        result = _parse_segment(seg, intent, video_duration)
        if isinstance(result, ClarificationError):
            return result
        segment_plans.append(result)

    # Merge all segments
    merged = _merge_plans(segment_plans)
    if isinstance(merged, ClarificationError):
        return merged

    # Determine inputs
    is_merge = 'merge' in intents
    if is_merge:
        if not has_files:
            return ClarificationError(
                reason="Please specify the files to merge.",
                code='no_input_file',
            )
        plan_inputs = resolved_files
    else:
        has_edit = any(merged.get(f) is not None for f in (
            'trim_start', 'trim_end', 'target_resolution', 'target_format',
            'target_filesize_mb', 'target_preset', 'audio_format',
        )) or merged.get('extract_audio', False)

        # URL or screen-record mode supplies its own input — skip file guard
        is_record = merged.get('record_screen', False)
        if has_edit and not has_files and not url and not is_record:
            return ClarificationError(
                reason="No input file specified.",
                code='no_input_file',
            )
        plan_inputs = [resolved_files[0]] if resolved_files else []

    # Pure download/record with no other recognised fields is still valid
    if not merged and not is_merge and not url:
        return ClarificationError(
            reason="I couldn't understand that request.",
            code='unrecognized',
        )

    # Normalize: if target_format is audio-only, route through extract_audio
    # so the builder emits -vn and the correct audio codec instead of video flags.
    if merged.get('target_format') in _AUDIO_FORMATS:
        merged['extract_audio'] = True
        if merged.get('audio_format') is None:
            merged['audio_format'] = merged['target_format']
        merged['target_format'] = None

    # --- URL / download post-processing ---
    if url:
        # Overlay download-specific params extracted from the full text
        dp = _extract_download_params(normalized)
        for k, v in dp.items():
            if not merged.get(k):  # don't overwrite values set by segment parsing
                merged[k] = v

        # target_resolution from a non-download segment → download_quality
        # (only when download_quality wasn't already set by a 'download' intent segment)
        if merged.get('target_resolution') and not merged.get('download_quality'):
            merged['download_quality'] = merged.pop('target_resolution')

        # target_format (video) → download_format (container for yt-dlp)
        if merged.get('target_format') and merged['target_format'] not in _AUDIO_FORMATS:
            if not merged.get('download_format'):
                merged['download_format'] = merged.pop('target_format')

        merged['download_url'] = url

        # Normalize: URL + extract_audio → download_audio_only (use yt-dlp -x path)
        if merged.get('extract_audio'):
            merged['download_audio_only'] = True
            merged['download_audio_format'] = merged.get('audio_format') or 'mp3'
            merged['extract_audio'] = False
            merged['audio_format'] = None

    return EditPlan(
        inputs=plan_inputs,
        trim_start=merged.get('trim_start'),
        trim_end=merged.get('trim_end'),
        target_resolution=merged.get('target_resolution'),
        target_format=merged.get('target_format'),
        target_filesize_mb=merged.get('target_filesize_mb'),
        target_preset=merged.get('target_preset'),
        extract_audio=merged.get('extract_audio', False),
        audio_format=merged.get('audio_format'),
        download_url=merged.get('download_url'),
        download_quality=merged.get('download_quality'),
        download_format=merged.get('download_format'),
        download_audio_only=merged.get('download_audio_only', False),
        download_audio_format=merged.get('download_audio_format'),
        download_subs=merged.get('download_subs', False),
        download_sub_lang=merged.get('download_sub_lang'),
        download_sub_auto=merged.get('download_sub_auto', False),
        download_playlist=merged.get('download_playlist'),
        download_thumbnail=merged.get('download_thumbnail', False),
        download_metadata=merged.get('download_metadata', False),
        target_width=merged.get('target_width'),
        target_height=merged.get('target_height'),
        target_scale_pct=merged.get('target_scale_pct'),
        crop_w=merged.get('crop_w'),
        crop_h=merged.get('crop_h'),
        crop_x=merged.get('crop_x'),
        crop_y=merged.get('crop_y'),
        crop_aspect=merged.get('crop_aspect'),
        record_screen=merged.get('record_screen', False),
        record_audio_device=merged.get('record_audio_device'),
        record_duration=merged.get('record_duration'),
    )
