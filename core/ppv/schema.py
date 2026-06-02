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


def validate(plan: dict) -> list[str]:
    """Return a list of human-readable errors (empty == valid)."""
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

    seen_ids = set()
    for i, s in enumerate(scenes):
        where = f"scenes[{i}]"
        if not isinstance(s, dict):
            errors.append(f"{where} must be an object"); continue
        sid = s.get("id")
        if not isinstance(sid, int):
            errors.append(f"{where}.id must be an int")
        elif sid in seen_ids:
            errors.append(f"{where}.id {sid} is duplicated")
        else:
            seen_ids.add(sid)
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
