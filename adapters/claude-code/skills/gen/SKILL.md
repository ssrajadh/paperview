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
/ `1:1`), **voice** (Supertonic `M1–M5`/`F1–F5`, default `M2`). Briefly state your interpretation
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
Run `~/.paperview/venv/bin/ppv components` for the exact component list and props. Write a JSON
object: `{ "meta": {title, aspect, voice}, "scenes": [ {id, narration, component, props}, … ] }`.

Guidance for a good plan:
- **Narrative arc:** open with `title`; motivate the problem; explain the core idea/method; show
  the architecture/key `figure`(s) by filename; typeset the key `equation`(s) in real LaTeX;
  cover results with `stats`; close with `outro`.
- **Narration** is spoken verbatim: 1–3 plain sentences per scene, **grounded in the paper's text**
  (no invented numbers/claims). Spell out symbols for TTS (e.g. "d sub k", "square root").
- **Visuals:** pick the component that best fits each beat — don't force a template. Use `figure`
  only with real extracted filenames; use `equation` for math (LaTeX in `tex`, no `$`); use
  `comparison`/`stats`/`bullets` to keep it varied. Respect the user's focus and length.
- Validate as you go: every scene needs `id`, `narration`, a valid `component`, and that
  component's required props (the CLI will reject an invalid plan).

## 5. Synthesize narration
```bash
~/.paperview/venv/bin/ppv tts "$WORK/plan.json" --out "$WORK"
```

## 6. (Optional but recommended) cheap visual check before the full render
Render one still per scene to catch layout problems cheaply, e.g.:
```bash
cd ~/.paperview/venv/../.. 2>/dev/null  # not needed; stills are optional
```
If you want stills, render a few frames with `npx remotion still` from `core/remotion`. Otherwise
proceed.

## 7. Render
```bash
~/.paperview/venv/bin/ppv render "$WORK/plan.json" --workdir "$WORK" --out "$WORK/explainer.mp4"
```
On a 16 GB machine, pass `--concurrency 4` to avoid memory thrash.

## 8. Report
Give the user the **MP4 path** (`$WORK/explainer.mp4`), the **render time** printed by the CLI,
the scene count, and a one-line honest note on where it might be weak (e.g. figures that couldn't
be extracted). Offer to tweak the plan and re-render.
