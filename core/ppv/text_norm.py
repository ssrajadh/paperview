"""Spoken-form normalization for narration, applied just before synthesis.

The phonemizer behind our TTS engines treats punctuation as punctuation, not as part of a
number — so a thousands comma reads as a clause break (`12,898` -> "twelve … eight hundred
ninety eight", dropping "thousand") and a decimal point reads as a sentence period
(`25.1` -> "twenty-five … one", no "point"). A handful of paper-isms are mangled too
(`Eq.` -> "eck", `vs.` -> "vee-ess", `10-20` -> "ten dash twenty", `~5` -> "tilde five").

`normalize_for_tts` rewrites these to the words we actually want spoken. It is applied
ONLY to the text handed to the TTS engine (and the cache key) — never to the plan — so burned
subtitles keep the original human-readable form (`12,898`, `$5`) while the audio says it right.
"""
from __future__ import annotations

import re

# Spelled-out paper abbreviations. Order matters: plural/longer keys before their singular
# prefixes so `Eqs.` isn't half-matched by the `Eq.` rule. Trailing `,?` swallows the comma
# that often follows e.g./i.e. so we don't double it.
_ABBR = (
    (re.compile(r"\bvs\.?(?=\s)"), "versus"),
    (re.compile(r"\bEqs\.\s*"), "Equations "),
    (re.compile(r"\bEq\.\s*"), "Equation "),
    (re.compile(r"\bFigs\.\s*"), "Figures "),
    (re.compile(r"\bFig\.\s*"), "Figure "),
    (re.compile(r"\be\.g\.,?"), "for example,"),
    (re.compile(r"\bi\.e\.,?"), "that is,"),
)

# Single-letter currency magnitudes ($3M, $2.4B) spelled out; word magnitudes ($1.5 billion)
# are kept verbatim.
_MAG_WORD = {"k": "thousand", "m": "million", "b": "billion", "t": "trillion"}

# A well-formed number: thousands-grouped (1,234 / 12,898) or plain, optional decimal. Anchored
# so `$5,` doesn't pull the trailing comma into the match.
_NUM = r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?"
_CURRENCY = re.compile(rf"\$({_NUM})(\s*(?:billion|million|trillion|thousand)|[kKmMbBtT])?")
_THOUSANDS = re.compile(r"(?<=\d),(?=\d{3}(?!\d))")
_DECIMAL = re.compile(r"(\d)\.(\d+)")
_RANGE = re.compile(r"(?<=\d)\s*-\s*(?=\d)")
_CARET = re.compile(r"(?<=\d)\s*\^\s*(?=\d)")
_APPROX = re.compile(r"~(?=\d)")


def _currency_sub(m: re.Match) -> str:
    num, mag = m.group(1), (m.group(2) or "").strip()
    if len(mag) == 1:  # glued letter magnitude, e.g. $3M
        mag = _MAG_WORD.get(mag.lower(), mag)
    return f"{num} {mag} dollars".replace("  ", " ") if mag else f"{num} dollars"


def normalize_for_tts(text: str) -> str:
    """Rewrite a narration string into the form we want the TTS engine to actually speak."""
    t = text
    # Currency first, on the raw number, so "$1.5 billion" -> "1.5 billion dollars" before the
    # comma/decimal rules below clean up "1.5" -> "1 point 5".
    t = _CURRENCY.sub(_currency_sub, t)
    # Numbers: drop thousands separators, then speak the decimal point and read the fraction
    # digit-by-digit (3.14 -> "three point one four", not "three point fourteen").
    t = _THOUSANDS.sub("", t)
    t = _DECIMAL.sub(lambda m: f"{m.group(1)} point {' '.join(m.group(2))}", t)
    # Symbols between digits (left alone elsewhere so GPT-4 / 5-fold survive).
    t = _RANGE.sub(" to ", t)
    t = _CARET.sub(" to the power ", t)
    t = _APPROX.sub("about ", t)
    for pat, rep in _ABBR:
        t = pat.sub(rep, t)
    return t
