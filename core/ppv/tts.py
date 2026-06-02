"""Narration synthesis with Supertonic (local, ONNX). One WAV per scene + durations."""
from __future__ import annotations
import json
from pathlib import Path

import numpy as np
import soundfile as sf


def synth(plan: dict, out_dir: str, voice: str | None = None, speed: float = 1.0,
          steps: int | None = None) -> list[dict]:
    from supertonic import TTS  # imported lazily so non-TTS commands stay fast

    out = Path(out_dir)
    audio = out / "audio"
    audio.mkdir(parents=True, exist_ok=True)

    from .schema import DEFAULT_VOICE, DEFAULT_TTS_STEPS
    voice = voice or plan.get("meta", {}).get("voice") or DEFAULT_VOICE
    steps = steps or DEFAULT_TTS_STEPS
    tts = TTS()  # supertonic-3, auto-downloads on first run
    style = tts.get_voice_style(voice)

    records = []
    for s in plan["scenes"]:
        wav, _ = tts.synthesize(s["narration"], style, total_steps=steps, speed=speed)
        wav = np.asarray(wav).squeeze()
        path = audio / f"scene{s['id']}.wav"
        tts.save_audio(wav, str(path))
        dur = round(sf.info(str(path)).duration, 3)
        records.append({"id": s["id"], "file": f"scene{s['id']}.wav", "duration": dur})
        print(f"  scene {s['id']:>2}: {dur:6.2f}s  -> {path.name}")

    (out / "durations.json").write_text(json.dumps(records, indent=2))
    total = sum(r["duration"] for r in records)
    print(f"  {len(records)} clips, total {total:.1f}s ({total/60:.1f} min)")
    return records
