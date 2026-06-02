---
description: "Generate a narrated, animated explainer video from a research paper PDF. Usage: /ppv:gen <pdf path or arxiv-style request, plus optional steering: length, focus, aspect, voice>."
disable-model-invocation: true
---

# /ppv:gen — paper PDF → narrated explainer video

The user's full request is: **$ARGUMENTS**

You are the *planner/composer*. You parse the request, read the paper, author a **scene plan**,
and drive the deterministic `ppv` CLI (parse → TTS → render). The CLI does the mechanical work;
your job is the script and the visual choices.

`ppv` lives at `~/.paperview/venv/bin/ppv` (run `/ppv:setup` first if it's missing).

## 1. Parse the request, then echo it back
From `$ARGUMENTS` extract: the **PDF path** (resolve `~`, relative paths; if missing or several
PDFs are plausible, **ask — don't guess**), and any steering: **length** (→ target scene count:
~1 scene per 12–15s, default 10–12 scenes ≈ 3 min), **focus**, **aspect** (`16:9` default / `9:16`
/ `1:1`), **voice** (Supertonic `M1–M5`/`F1–F5`, default `F2`). Briefly state your interpretation
(*"paper = X.pdf · ~3 min · focus = … · 16:9 — generating now"*) before the long steps.

## 2. Set up a run directory
```bash
WORK=~/.paperview/runs/$(date +%s); mkdir -p "$WORK"
```

## 3. Parse the PDF
```bash
~/.paperview/venv/bin/ppv parse "<pdf>" --out "$WORK"
```
Then **read `$WORK/parse.json`** (per-page text) and **view every figure** in `$WORK/assets/`
with the Read tool — you must know what each `fig_*.png` actually depicts before you reference it.

## 4. Author the scene plan → `$WORK/plan.json`
Run `~/.paperview/venv/bin/ppv components` for the component list + props, and
`~/.paperview/venv/bin/ppv schema` for the full plan contract (meta fields, valid `aspect`/`voice`).
Write a JSON object: `{ "meta": {title, aspect, voice}, "scenes": [ {narration, component, props}, … ] }`.
**`id` is optional — ppv auto-assigns it by order, so you can omit it** (or use readable names; they're
renumbered).

Guidance for a good plan:
- **Narrative arc:** open with `title`; motivate the problem; explain the core idea/method; show
  the architecture/key `figure`(s) by filename; typeset the key `equation`(s) in real LaTeX;
  cover results with `stats`; close with `outro`.
- **Narration** is spoken verbatim: 1–3 plain sentences per scene, **grounded in the paper's text**
  (no invented numbers/claims). **Write for TTS** — it reads text literally and has no math sense:
  - Spell out symbols/operators: "d sub k", "square root", "less than or equal to".
  - **Spell single-letter variables as their letter name**, or TTS voices them as a sound, not a
    letter (e.g. matrix "a" → says "uh", not "ay"). Use: a→"ay", e→"ee", i→"eye", o→"oh", q→"cue",
    k→"kay", x→"eks", w→"double-u", y→"why", h→"aitch" (others mostly read fine). E.g.
    *"the query vector cue and the key vector kay"*. `ppv validate` warns on lone letters (except
    a/A/I, which collide with articles — handle those yourself).
- **Visuals:** pick the component that best fits each beat — don't force a template. Use `figure`
  only with real extracted filenames; use `equation` for math (LaTeX in `tex`, no `$`); use
  `comparison`/`stats`/`bullets` to keep it varied. Respect the user's focus and length.
- Each scene needs `narration`, a valid `component`, and that component's required props.

## 4b. Validate the plan (cheap — do this before spending TTS/render time)
```bash
~/.paperview/venv/bin/ppv validate "$WORK/plan.json" --assets "$WORK/assets"
```
Fixes the slow failures up front: invalid components/props (errors, exit 2) and **warnings** for
TTS-hostile symbols in narration (raw `≤ → √ ⟹` etc. — spell them out) and `figure` srcs that don't
exist. Fix anything it flags, then proceed.

## 5. Synthesize narration
```bash
~/.paperview/venv/bin/ppv tts "$WORK/plan.json" --out "$WORK"
```
(`ppv tts --list-voices` lists the presets if the user asked for a specific voice.)

## 6. (Recommended) cheap visual check before the full render
A full render takes minutes; a still takes seconds. Spot-check dense scenes (equations, long text,
figures) for overflow/clipping first:
```bash
~/.paperview/venv/bin/ppv preview "$WORK/plan.json" --workdir "$WORK" --scene 7   # one scene -> PNG
~/.paperview/venv/bin/ppv preview "$WORK/plan.json" --workdir "$WORK" --all       # every scene
```
**Read the PNG(s)** with the Read tool and fix any clipped/overflowing scenes in the plan before
rendering. (Stills need only the figures in `$WORK/assets`; no TTS required.)

## 7. Render
```bash
~/.paperview/venv/bin/ppv render "$WORK/plan.json" --workdir "$WORK" --out "$WORK/explainer.mp4"
```
Defaults to **1080p @ 30fps**. Resolution is the big speed/size lever — `--resolution 810p` (or `540p`)
renders **much** faster and smaller, and `--draft` (810p @ 24fps) is the fast-iteration preset; use it
for previews and re-render at 1080p only for the final. **A full-length 1080p render can take tens of
minutes** — tell the user the resolution/time tradeoff up front and prefer `--draft` while iterating.
`--crf N` (higher = smaller file) trims size without dropping resolution. Concurrency is auto-detected
from cores + free RAM. The render is quiet — add `--progress` and/or background it for long jobs.

## 8. Report
Give the user the **MP4 path** (`$WORK/explainer.mp4`), the **render time** printed by the CLI,
the scene count, and a one-line honest note on where it might be weak (e.g. figures that couldn't
be extracted). Offer to tweak the plan and re-render.
