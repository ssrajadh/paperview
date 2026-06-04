"""The scene-plan contract shared by the agent (planner) and the renderer.

A scene plan is a JSON object:
  { "meta": { "title": str, "aspect": "16:9"|"9:16"|"1:1", "voice": str },
    "scenes": [ { "id": int, "narration": str,
                  "component": <one of COMPONENTS>, "props": { ... } }, ... ] }

`narration` is spoken verbatim by TTS. `component` + `props` choose the on-screen
visual from a fixed library (v1: no freeform code). Keep narration 1-3 sentences.
"""
from __future__ import annotations

# component name -> (required props, optional props, one-line purpose)
COMPONENTS: dict[str, dict] = {
    "title": {
        "required": ["title"],
        "optional": ["subtitle"],
        "purpose": "Opening title card. title + optional subtitle (authors/venue/year).",
    },
    "statement": {
        "required": ["text"],
        "optional": ["eyebrow"],
        "purpose": "One big centered statement/idea. Optional small eyebrow label above.",
    },
    "bullets": {
        "required": ["items"],
        "optional": ["heading"],
        "purpose": "A short list (2-5 items) that reveals one at a time. items: [str].",
    },
    "figure": {
        "required": ["src"],
        "optional": ["caption", "label"],
        "purpose": "Show an extracted figure (src = asset filename from `ppv parse`) on a card. "
                   "Optional caption (below) and label (overlay tag).",
    },
    "equation": {
        "required": ["tex"],
        "optional": ["heading", "caption"],
        "purpose": "Typeset a LaTeX equation (KaTeX). tex = LaTeX string (no $). Optional heading/caption.",
    },
    "comparison": {
        "required": ["rowLabels", "columns"],
        "optional": ["heading"],
        "purpose": "Compare 2 columns across rows. rowLabels: [str]; "
                   "columns: [{title: str, highlight?: bool, values: [str]}] (values aligns with rowLabels).",
    },
    "stats": {
        "required": ["items"],
        "optional": ["heading"],
        "purpose": "Big number callouts. items: [{value: str, label: str, highlight?: bool}].",
    },
    "outro": {
        "required": ["text"],
        "optional": ["tags"],
        "purpose": "Closing card. text = final line. Optional tags: [str] that fade in around it.",
    },
}

ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}

# Backdrop palettes (must match remotion/src/theme.tsx THEMES). A theme only changes the
# ambient background; content colors are shared, so legibility is identical across themes.
THEMES = ["midnight", "slate", "dusk"]
DEFAULT_THEME = "midnight"

# Supertonic voice presets. M# = male, F# = female; audition with `ppv tts --voice <id>`.
VOICES = ["M1", "M2", "M3", "M4", "M5", "F1", "F2", "F3", "F4", "F5"]
DEFAULT_VOICE = "F2"

# Output resolution presets -> Remotion render scale vs the 1080 base. Only scales that
# are integer-exact for every aspect AND exact in binary float (avoids the 720.036 trap):
# 0.6667 (true 720p) is NOT reachable via --scale from 1920x1080 — 810p is the stand-in.
# Render cost falls faster than pixel count (the browser paints fewer pixels per frame).
RESOLUTIONS = {"1080p": 1.0, "810p": 0.75, "540p": 0.5}
DEFAULT_RESOLUTION = "1080p"
DEFAULT_FPS = 30
# `--draft`: fast, smaller, for iteration. Lower res + fps; a deliberate opt-in, NOT
# hardware-driven (same plan must render identically everywhere — see notes D5/D12).
DRAFT_RESOLUTION = "810p"
DRAFT_FPS = 24

# Supertonic diffusion steps. NOT monotonic — 16 was the empirical sweet spot (judged most
# natural, beating both 8 and 32; higher over-smooths prosody). Don't naively raise this.
# ~linear cost (16 ≈ 2x of 8) but TTS is a minority of the pipeline. Override: `ppv tts --steps`.
DEFAULT_TTS_STEPS = 16

# Characters TTS reads poorly (math/logic symbols) — narration should spell these out.
_TTS_HOSTILE = set("¬≤≥⟹⟸⟺↔→←×÷≈≠≅≡√∞∑∏∫∂∇∈∉⊂⊆⊃⊇∪∩∧∨∀∃±∓·∘°µΩ⊗⊕")
# Lone single letters usually mean a math variable, which TTS voices as a sound, not the
# letter name ("a" -> schwa "uh", not "ay"). Exclude real one-letter words (a/A/I) — those
# collide with articles/pronouns and would be too noisy to flag (the skill steers the planner
# to spell variable 'a' as "ay"). Catch the rest as a reminder to spell the letter name.
_LETTER_WORDS = {"a", "A", "I"}


def normalize(plan: dict) -> dict:
    """Fill in the fields ppv owns so the agent needn't. Currently: (re)assign each
    scene's `id` by 1-based array order — agents can omit ids or use any value
    (readable strings included); ppv renumbers them. Mutates and returns `plan`."""
    if isinstance(plan, dict) and isinstance(plan.get("scenes"), list):
        for i, s in enumerate(plan["scenes"], 1):
            if isinstance(s, dict):
                s["id"] = i
    return plan


def validate(plan: dict) -> list[str]:
    """Return a list of human-readable errors (empty == valid). `id` is not checked
    here — it's auto-assigned by `normalize()`."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["plan must be a JSON object"]
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return ["plan.scenes must be a non-empty array"]

    meta = plan.get("meta", {})
    aspect = meta.get("aspect", "16:9")
    if aspect not in ASPECTS:
        errors.append(f"meta.aspect '{aspect}' not in {sorted(ASPECTS)}")
    voice = meta.get("voice")
    if voice is not None and voice not in VOICES:
        errors.append(f"meta.voice '{voice}' not in {VOICES}")
    res = meta.get("resolution")
    if res is not None and res not in RESOLUTIONS:
        errors.append(f"meta.resolution '{res}' not in {sorted(RESOLUTIONS)}")
    fps = meta.get("fps")
    if fps is not None and (not isinstance(fps, int) or fps <= 0):
        errors.append(f"meta.fps '{fps}' must be a positive integer")
    caps = meta.get("captions")
    if caps is not None and not isinstance(caps, bool):
        errors.append(f"meta.captions '{caps}' must be a boolean")
    theme = meta.get("theme")
    if theme is not None and theme not in THEMES:
        errors.append(f"meta.theme '{theme}' not in {THEMES}")

    for i, s in enumerate(scenes):
        where = f"scenes[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{where} must be an object"); continue
        narration = s.get("narration")
        if not isinstance(narration, str) or not narration.strip():
            errors.append(f"{where}.narration must be a non-empty string")
        comp = s.get("component")
        if comp not in COMPONENTS:
            errors.append(f"{where}.component '{comp}' not in {sorted(COMPONENTS)}")
            continue
        props = s.get("props", {})
        if not isinstance(props, dict):
            errors.append(f"{where}.props must be an object"); continue
        for req in COMPONENTS[comp]["required"]:
            if req not in props:
                errors.append(f"{where} (component '{comp}') missing required prop '{req}'")
    return errors


def lint(plan: dict, assets_dir=None) -> list[str]:
    """Return non-fatal warnings (empty == clean). Catches things that render/synth
    fine but produce bad *output*: TTS-hostile symbols in narration (mangled audio)
    and, if `assets_dir` is given, `figure` srcs that don't exist on disk."""
    import re
    from pathlib import Path
    warnings: list[str] = []
    scenes = plan.get("scenes") if isinstance(plan, dict) else None
    if not isinstance(scenes, list):
        return warnings
    for i, s in enumerate(scenes):
        if not isinstance(s, dict):
            continue
        where = f"scenes[{i}]"
        text = s.get("narration", "")
        if isinstance(text, str):
            bad = sorted({c for c in text if c in _TTS_HOSTILE})
            if bad:
                warnings.append(f"{where}.narration has TTS-hostile symbols {bad} — "
                                f"spell them out (e.g. '≤' → 'less than or equal to')")
            if "\\" in text or "$" in text:
                warnings.append(f"{where}.narration looks like it contains raw LaTeX — "
                                f"TTS reads it literally; write the spoken words instead")
            lone = sorted({m for m in re.findall(r"(?<![A-Za-z'])([A-Za-z])(?![A-Za-z'])", text)
                           if m not in _LETTER_WORDS})
            if lone:
                warnings.append(f"{where}.narration has lone letters {lone} — if these are math "
                                f"variables, spell the letter name (q→'cue', x→'eks', k→'kay') so "
                                f"TTS says the letter, not a sound")
        if assets_dir is not None and s.get("component") == "figure":
            src = (s.get("props") or {}).get("src")
            if src and not (Path(assets_dir) / src).exists():
                warnings.append(f"{where} figure src '{src}' not found in {assets_dir}")
    return warnings


def plan_schema() -> dict:
    """Full JSON Schema for a scene plan (meta + scene envelope). Per-component
    `props` are described by `ppv components`, referenced via $comment."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "PaperView scene plan",
        "type": "object",
        "required": ["scenes"],
        "properties": {
            "meta": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "aspect": {"enum": sorted(ASPECTS), "default": "16:9"},
                    "voice": {"enum": VOICES, "default": DEFAULT_VOICE,
                              "description": "Supertonic preset; --voice overrides meta.voice."},
                    "resolution": {"enum": sorted(RESOLUTIONS), "default": DEFAULT_RESOLUTION,
                                   "description": "Output size; --resolution/--draft override."},
                    "fps": {"type": "integer", "default": DEFAULT_FPS,
                            "description": "Frame rate; --fps/--draft override."},
                    "captions": {"type": "boolean", "default": False,
                                 "description": "Burn narration as subtitles; --captions/--no-captions override."},
                    "theme": {"enum": THEMES, "default": DEFAULT_THEME,
                              "description": "Backdrop palette; --theme overrides meta.theme."},
                    "audio": {"type": "boolean", "default": True},
                },
            },
            "scenes": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "required": ["narration", "component", "props"],
                    "properties": {
                        "id": {"type": "integer",
                               "description": "Optional — auto-assigned by array order; agents may omit."},
                        "narration": {"type": "string", "description": "Spoken verbatim by TTS (1-3 sentences)."},
                        "component": {"enum": sorted(COMPONENTS)},
                        "props": {"type": "object",
                                  "$comment": "Required/optional props per component: run `ppv components`."},
                    },
                },
            },
        },
    }


def schema_doc() -> str:
    """Human-readable component reference (embedded in the agent skill + `ppv components`)."""
    lines = ["Scene-plan component library (choose `component` + fill `props`):", ""]
    for name, spec in COMPONENTS.items():
        req = ", ".join(spec["required"]) or "—"
        opt = ", ".join(spec["optional"]) or "—"
        lines.append(f"• {name}: {spec['purpose']}")
        lines.append(f"    required props: {req}")
        lines.append(f"    optional props: {opt}")
    return "\n".join(lines)
