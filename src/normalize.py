from __future__ import annotations
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from vocabulary import (
    SLANG_MAP, ABBREVIATIONS, CONTRACTIONS,
    HEDGE_WORDS, FILLER_PHRASES,
)


def _word_sub(text: str, mapping: dict[str, str]) -> str:
    for key in sorted(mapping, key=len, reverse=True):
        text = re.sub(r'\b' + re.escape(key) + r'\b', mapping[key], text, flags=re.IGNORECASE)
    return text


def _strip_phrases(text: str, phrases: list[str]) -> str:
    for phrase in sorted(phrases, key=len, reverse=True):
        text = re.sub(r'\b' + re.escape(phrase) + r'\b', ' ', text, flags=re.IGNORECASE)
    return text


_TIMESTAMP_RE = re.compile(r'\d+:\d\d(?:\.\d+)?')
# Matches standalone integers and decimals (e.g. "2", "30", "1.5") that should
# not be treated as SLANG_MAP keys like "2"→"to" or "4"→"for".
_BARE_NUMBER_RE = re.compile(r'(?<![:\w])\d+(?:\.\d+)?(?![\w:])')


def normalize(text: str) -> str:
    text = text.lower()

    # Protect timestamps (e.g. "1:30", "2:45") by replacing them with
    # placeholders before word-level substitutions, then restoring them.
    timestamps = _TIMESTAMP_RE.findall(text)
    placeholders: list[str] = []
    for i, ts in enumerate(timestamps):
        ph = f'__TS{i}__'
        placeholders.append(ph)
        text = text.replace(ts, ph, 1)

    # Protect bare numbers (e.g. "2", "30", "25") so SLANG_MAP entries like
    # "2"→"to" and "4"→"for" do not corrupt numeric values in the text.
    bare_numbers: list[str] = _BARE_NUMBER_RE.findall(text)
    num_placeholders: list[str] = []
    for i, num in enumerate(bare_numbers):
        ph = f'__NUM{i}__'
        num_placeholders.append(ph)
        text = re.sub(r'(?<![:\w])' + re.escape(num) + r'(?![\w:])', ph, text, count=1)

    text = _word_sub(text, CONTRACTIONS)
    text = _word_sub(text, SLANG_MAP)
    text = _word_sub(text, ABBREVIATIONS)

    # Restore bare numbers before ABBREVIATIONS further expands units
    # Actually restore after ABBREVIATIONS since units like "m"→"minutes" act on words
    # We restore after all substitutions
    for ph, num in zip(num_placeholders, bare_numbers):
        text = text.replace(ph, num)
    text = _strip_phrases(text, FILLER_PHRASES)
    text = _strip_phrases(text, HEDGE_WORDS)

    # Restore timestamps
    for ph, ts in zip(placeholders, timestamps):
        text = text.replace(ph, ts)

    text = re.sub(r'\s+', ' ', text).strip()
    return text
