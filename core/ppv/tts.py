"""Narration synthesis: one WAV per scene + durations, via a pluggable TTS provider.

The engine is chosen per run (Kokoro by default — see `providers.py`); this module only
orchestrates: it resolves the provider/voice, walks the scenes, and manages the cache.

Per-scene results are cached by the provider's fingerprint (engine id + version + voice +
knobs) plus the normalized narration, under ~/.paperview/cache/tts/, so re-running after
editing a few scenes only re-synthesizes what changed — and an all-hit run never even builds
the engine. Bypass with `ppv tts --no-cache`.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from pathlib import Path

import soundfile as sf

from .providers import get_provider
from .text_norm import normalize_for_tts

CACHE_DIR = Path.home() / ".paperview" / "cache" / "tts"


def _cache_key(prov, text: str, voice: str, speed: float) -> str:
    norm = " ".join(text.split())  # collapse whitespace; keep case (TTS is case-sensitive)
    raw = f"{prov.fingerprint(voice, speed)}|{norm}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def synth(plan: dict, out_dir: str, provider: str | None = None, voice: str | None = None,
          speed: float = 1.0, cache: bool = True) -> list[dict]:
    out = Path(out_dir)
    audio = out / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    meta = plan.get("meta", {})
    prov = get_provider(provider or meta.get("provider"))
    voice = voice or meta.get("voice") or prov.default_voice
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    records, hits = [], 0
    for s in plan["scenes"]:
        path = audio / f"scene{s['id']}.wav"
        # Speak the spoken-form text (numbers/abbreviations rewritten); the plan — and so any
        # burned subtitle — keeps the original human-readable narration.
        spoken = normalize_for_tts(s["narration"])
        cpath = (CACHE_DIR / f"{_cache_key(prov, spoken, voice, speed)}.wav"
                 if cache else None)
        if cpath is not None and cpath.exists():
            shutil.copy2(cpath, path)
            hits += 1
            tag = "cache"
        else:
            prov.render(spoken, voice, speed, str(path))
            if cpath is not None:
                shutil.copy2(path, cpath)
            tag = "synth"
        dur = round(sf.info(str(path)).duration, 3)
        records.append({"id": s["id"], "file": f"scene{s['id']}.wav", "duration": dur})
        print(f"  scene {s['id']:>2}: {dur:6.2f}s  [{tag}] -> {path.name}")

    (out / "durations.json").write_text(json.dumps(records, indent=2))
    total = sum(r["duration"] for r in records)
    print(f"  {len(records)} clips ({hits} cached) via {prov.id}, "
          f"total {total:.1f}s ({total/60:.1f} min)")
    return records
