---
description: "Generate a narrated, animated explainer video from a research paper (PDF) or a codebase/repo. Usage: /ppv:gen <pdf path, arxiv-style request, OR a codebase path/topic, plus optional steering: length, focus, aspect, voice>."
disable-model-invocation: true
---

# /ppv:gen — paper or codebase → narrated explainer video

The user's full request is: **$ARGUMENTS**

You are the *planner/composer*. You parse the request, read the source (a research paper **or** a
codebase), author a **scene plan**, and drive the deterministic `ppv` CLI (parse → TTS → render).
The CLI does the mechanical work; your job is the script and the visual choices.

`ppv` lives at `~/.paperview/venv/bin/ppv` (run `/ppv:setup` first if it's missing).

## 1. Parse the request, then echo it back
From `$ARGUMENTS` extract: the **source** — a **PDF**, a **text/Markdown** file, or a **codebase**
(a local repo/directory, a set of source files, a **remote git URL** like
`https://github.com/owner/repo`, or a "explain project X" topic) — resolve `~`, relative
paths; if missing or ambiguous, **ask — don't guess**. A codebase takes a different path through
the steps below (no `ppv parse`, no figures — see §3). Then any steering:
- **length / duration** — a target time (e.g. *"2 minutes"*, *"~5 min"*) → target scene count at
  ~1 scene per 12–15s (default 10–12 scenes ≈ 3 min) **and** a per-scene narration word budget
  (~2.5 words/sec, so a 14s scene ≈ 35 words). Size narration to hit the target; TTS finalizes it.
- **depth / audience** — *intro / general* vs *expert*, *intuition-heavy* vs *math-heavy*. This sets
  the narration register and the component mix: a general-audience cut leans on `statement`/`bullets`/
  `figure` and explains terms; an expert cut spends more on `equation`/`comparison` and assumes
  vocabulary. Keep claims calibrated either way (§4). For papers/repos with an algorithm or key
  source snippet, use `code` — paste a real, focused snippet (~6-16 lines), set `lang`, and use
  `highlightLines` so the narration can walk through specific lines.
- **focus** — a sub-topic to emphasize (spend more scenes there, trim the rest).
- **aspect** (`16:9` default / `9:16` / `1:1`), **provider/voice** (default Kokoro, voice `af_heart`;
  run `ppv tts --list-voices` for the voices each provider offers),
  **captions** (on/off — burned-in subtitles, default off; set `meta.captions` or pass `--captions`).

Briefly state your interpretation (*"paper = X.pdf · ~2 min (8 scenes) · expert · 16:9 — generating
now"*) before the long steps.

## 2. Set up a run directory — named for the topic, not a timestamp
Derive a short **kebab-case slug** from the source's topic (the paper title or the codebase/project
name, e.g. `attention-is-all-you-need`, `redis-event-loop`) — keep it lowercase, ascii, `< ~40` chars.
Use that one slug for **both** the run directory and the final video filename so runs are
self-describing instead of bare numbers:
```bash
SLUG=attention-is-all-you-need   # <- your topic slug
WORK=~/.paperview/runs/$SLUG; [ -e "$WORK" ] && WORK="$WORK-$(date +%y%m%d-%H%M%S)"  # avoid clobber
mkdir -p "$WORK"
```
Reuse `$SLUG` when naming the MP4 in §7 (`$WORK/$SLUG.mp4`). If you can't infer a topic yet, pick the
best guess from the request/filename now — a readable name beats a timestamp.

## 3. Parse the source
**Paper / document source** (PDF, Markdown, text):
```bash
~/.paperview/venv/bin/ppv parse "<source>" --out "$WORK"   # PDF, Markdown, or text
```
`ppv parse` handles each type natively — **for a Markdown/text source, never convert it to a PDF
first** (lossy round-trip); `ppv parse` reads it directly. Then **read `$WORK/parse.json`** (the
text) and **view every figure** in `$WORK/assets/` with the Read tool — you must know what each
figure actually depicts before you reference it. (A text source with no images yields no figures —
that's fine; lean on `equation`/`bullets`/`statement`/`comparison` instead.)

**Codebase source** (a local repo/directory, a set of files, or a **remote git URL**): **skip
`ppv parse` entirely** — there's no document to extract. If the source is a remote git URL (e.g.
`https://github.com/owner/repo`, a `*.git` URL, or `git@…`), **shallow-clone it into the run dir
first** and treat that clone as the codebase:
```bash
git clone --depth 1 "<url>" "$WORK/repo"   # add `--branch <ref>` if the user named a branch/tag
```
(If the URL points at a subpath — `…/tree/main/pkg/x` — clone the repo *root*, then focus on that
subdir. If the clone fails, e.g. a private repo, tell the user and ask them to clone it locally and
pass the path.) Then **read the code directly with your own tools**: start at the entry
points and README, map the architecture (modules, data flow, key abstractions), then open the few
functions/types that carry the core idea. There are no extracted figures, so the visual load falls
on `mermaid` (architecture/flow/sequence diagrams), `code` (real snippets — paste actual source,
set `lang`, use `highlightLines` or `diff` mode), `bullets`, and `comparison`. Skip §3b (no
equations). Then go straight to §4 and author the plan grounded in the code you actually read — the
same faithfulness bar applies (don't describe functions/behavior the code doesn't have).

## 3b. Extract the paper's real equations (arXiv) — don't typeset math from memory
Reconstructing equations from your own recall of the paper is the validated #1 faithfulness risk.
When the source is an arXiv paper — an id/URL, or a PDF that prints `arXiv:NNNN.NNNNN` on page 1 —
pull the **actual** LaTeX instead:
```bash
~/.paperview/venv/bin/ppv math "<source path or arXiv id/URL>" --out "$WORK"
```
Read `$WORK/math.json`: it lists the paper's real display equations as KaTeX-ready `tex` (custom
macros already expanded), each with the preceding sentence as `context` to help you place it. **Copy
these `tex` strings verbatim into your `equation` scenes** rather than writing the math yourself. If
`math.json` carries a `note` (no arXiv id, or not on arXiv), transcribe equations carefully from the
PDF/figures instead — and prefer fewer, high-confidence equations over guessed ones.

## 4. Author the scene plan → `$WORK/plan.json`
Run `~/.paperview/venv/bin/ppv components` for the component list + props, and
`~/.paperview/venv/bin/ppv schema` for the full plan contract (meta fields, valid `aspect`/`voice`).
Write a JSON object: `{ "meta": {title, aspect, voice, theme}, "scenes": [ {narration, component, props}, … ] }`.

**Always set `meta.theme`** — don't leave it to the default. You've read the paper, so pick the
backdrop that fits its field and tone (this is the auto-selection; the user shouldn't have to ask):
- `midnight` (deep navy/blue) — default mood; core ML, theory, NLP, general CS.
- `slate` (cool neutral gray-blue) — systems, infrastructure, security, networking, databases, hardware.
- `dusk` (warm plum→amber) — vision, graphics, generative media, HCI, biology, or anything where a
  softer/editorial feel suits the subject.
Pick the closest fit; when genuinely unsure, use `midnight`. A user-specified look (or `--theme`)
always wins.
**`id` is optional — ppv auto-assigns it by order, so you can omit it** (or use readable names; they're
renumbered).

Guidance for a good plan:
- **Narrative arc:** open with `title`; motivate the problem; explain the core idea/method; show
  the architecture/key `figure`(s) by filename; typeset the key `equation`(s) in real LaTeX;
  cover results with `stats`; close with `outro`.
- **Narration** is spoken verbatim: 1–3 plain sentences per scene, **grounded in the paper's text**
  (no invented numbers/claims).
- **Don't overstate — calibrate claims to what the paper actually shows.** This is the #1 faithfulness
  slip on unfamiliar papers (validated by external judges): the model nudges claims slightly too
  strong. Avoid unearned superlatives — don't say **"state of the art"** unless the paper does;
  attribute comparative results to the **specific baselines/benchmarks evaluated** ("outperforms the
  prior methods on TriGap and UCIT", not "the best, period"). Don't assert a result is "proven" or
  "largest/exactly" beyond the evidence. Prefer the paper's own hedging. When unsure, state the
  narrower, supportable version.
- **Write for TTS** — it reads text literally and has no math sense:
  - Spell out symbols/operators: "d sub k", "square root", "less than or equal to".
  - **Spell single-letter variables as their letter name**, or TTS voices them as a sound, not a
    letter (e.g. matrix "a" → says "uh", not "ay"). Use: a→"ay", e→"ee", i→"eye", o→"oh", q→"cue",
    k→"kay", x→"eks", w→"double-u", y→"why", h→"aitch" (others mostly read fine). E.g.
    *"the query vector cue and the key vector kay"*. `ppv validate` warns on lone letters (except
    a/A/I, which collide with articles — handle those yourself).
- **Visuals:** pick the component that best fits each beat — don't force a template. Use `figure`
  only with real extracted filenames; use `equation` for math (LaTeX in `tex`, no `$` — prefer the
  verbatim strings from `$WORK/math.json`, step 3b); use `mermaid` for an architecture / data-flow /
  pipeline / sequence diagram when there's no real figure to show (the go-to for codebases and for
  method overviews — keep it to ~3-10 nodes); use `code` for real source snippets (and `code` with
  `diff: true` for a before/after change); use `comparison`/`stats`/`bullets` to keep it varied.
  Respect the user's focus and length.
- **Cite every reproduced figure.** When you use `figure`, set its `caption` to a source
  attribution (e.g. *"Figure 2 — Vaswani et al., 2017"*). Papers' figures are copyrighted, so
  they're always embedded **with credit**, never anonymously.
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
~/.paperview/venv/bin/ppv render "$WORK/plan.json" --workdir "$WORK" --out "$WORK/$SLUG.mp4"
```
Name the MP4 with the run's `$SLUG` (§2), not a generic `explainer.mp4`, so the file is
self-describing. Defaults to **1080p @ 30fps**. Resolution is the big speed/size lever — `--resolution 810p` (or `540p`)
renders **much** faster and smaller, and `--draft` (810p @ 24fps) is the fast-iteration preset; use it
for previews and re-render at 1080p only for the final. **A full-length 1080p render can take tens of
minutes** — tell the user the resolution/time tradeoff up front and prefer `--draft` while iterating.
`--crf N` (higher = smaller file) trims size without dropping resolution. `--captions` burns the
narration in as subtitles (default off; use it when the user asks for captions/subtitles or an
accessible cut). The backdrop palette normally comes from `meta.theme` (you set it in §4); `--theme midnight|slate|dusk`
is only an override for when the user explicitly asks for a different look mid-render. Concurrency is
auto-detected from cores + free RAM. The render is quiet — add `--progress` and/or background it for
long jobs.

## 8. Report
Give the user the result as a **clickable link** so they don't have to hunt the filesystem —
present the MP4 as a markdown link, e.g. `[▶ play attention-is-all-you-need.mp4](file:///home/.../attention-is-all-you-need.mp4)`
(absolute `file://` path, named with the run's `$SLUG`). `ppv render` also prints the path as a
clickable terminal hyperlink (some terminals — GNOME Terminal, VS Code — need Ctrl/⌘-click to follow it).
**Don't auto-open it** (a player stealing focus minutes later is disruptive) — let the user click
when ready. Also report the **render time**, scene count, and a one-line honest note on where it
might be weak (e.g. figures that couldn't be extracted). Offer to tweak the plan and re-render.
