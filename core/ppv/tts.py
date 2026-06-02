"""Narration synthesis with Supertonic (local, ONNX). One WAV per scene + durations.

Per-scene results are cached by (supertonic version, voice, steps, speed, normalized
narration) under ~/.paperview/cache/tts/, so re-running after editing a few scenes only
re-synthesizes what changed — and an all-hit run never even loads the model. Bypass with
`ppv tts --no-cache`.
"""
from __future__ import annotations
import hashlib
import json
import shutil
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import soundfile as sf

CACHE_DIR = Path.home() / ".paperview" / "cache" / "tts"


def _st_version() -> str:
    try:
        return version("supertonic")
    except PackageNotFoundError:
        return "unknown"


def _cache_key(text: str, voice: str, steps: int, speed: float) -> str:
    norm = " ".join(text.split())  # collapse whitespace; keep case (TTS is case-sensitive)
    raw = f"st{_st_version()}|{voice}|{steps}|{speed}|{norm}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def synth(plan: dict, out_dir: str, voice: str | None = None, speed: float = 1.0,
          steps: int | None = None, cache: bool = True) -> list[dict]:
    out = Path(out_dir)
    audio = out / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    from .schema import DEFAULT_VOICE, DEFAULT_TTS_STEPS
    voice = voice or plan.get("meta", {}).get("voice") or DEFAULT_VOICE
    steps = steps or DEFAULT_TTS_STEPS
    if cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # lazy: build the (expensive) ONNX engine only on the first cache miss
    engine: dict = {"tts": None, "style": None}

    def ensure():
        if engine["tts"] is None:
            from supertonic import TTS  # imported lazily so non-TTS commands stay fast
            e = TTS()  # supertonic-3, auto-downloads on first run
            engine["tts"], engine["style"] = e, e.get_voice_style(voice)
        return engine["tts"], engine["style"]

    records, hits = [], 0
    for s in plan["scenes"]:
        path = audio / f"scene{s['id']}.wav"
        cpath = CACHE_DIR / f"{_cache_key(s['narration'], voice, steps, speed)}.wav" if cache else None
        if cpath is not None and cpath.exists():
            shutil.copy2(cpath, path)
            hits += 1
            tag = "cache"
        else:
            e, style = ensure()
            wav, _ = e.synthesize(s["narration"], style, total_steps=steps, speed=speed)
            e.save_audio(np.asarray(wav).squeeze(), str(path))
            if cpath is not None:
                shutil.copy2(path, cpath)
            tag = "synth"
        dur = round(sf.info(str(path)).duration, 3)
        records.append({"id": s["id"], "file": f"scene{s['id']}.wav", "duration": dur})
        print(f"  scene {s['id']:>2}: {dur:6.2f}s  [{tag}] -> {path.name}")

    (out / "durations.json").write_text(json.dumps(records, indent=2))
    total = sum(r["duration"] for r in records)
    print(f"  {len(records)} clips ({hits} cached), total {total:.1f}s ({total/60:.1f} min)")
    return records
