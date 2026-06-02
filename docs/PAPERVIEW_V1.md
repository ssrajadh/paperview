# PaperView (`/ppv`) — V1 Launch Plan & Project Handoff

> **Audience:** the next agent/engineer who picks this up cold. This document assumes **zero prior context** and tries to be exhaustive: what exists, why it works, where it breaks, and everything that must happen before a v1 launch. Read Part A end‑to‑end before touching code.
>
> **Status:** working MVP exists (proof‑of‑concept, single paper). No v1 code yet.
> **Current code location:** `/home/soham/Documents/paper2video/` (will be renamed `paperview/`).
> **Last updated:** 2026‑05‑31.

---

## Table of contents

- **Part A — Project context (what exists today)**
  - A1. Elevator pitch & the hypothesis we tested
  - A2. What the MVP proved (and didn't)
  - A3. Exact stack & versions
  - A4. Current repo layout, file by file
  - A5. The 6‑stage pipeline as built (commands + I/O)
  - A6. Critical technical learnings & API quirks
  - A7. Honest limitations discovered (where it breaks)
  - A8. How to reproduce the MVP from scratch
- **Part B — V1 vision & scope**
- **Part C — Target architecture**
- **Part D — V1 workstreams (the bulk of the work)**
- **Part E — Cross‑cutting concerns**
- **Part F — Open decisions for the human**
- **Part G — Suggested milestones / sequencing**
- **Part H — References & links**
- **Appendix — exact versions, commands, file inventory**

---

# Part A — Project context (what exists today)

## A1. Elevator pitch & the hypothesis we tested

**PaperView turns a research‑paper PDF into a narrated, animated explainer video using *deterministic* rendering — not generative video.** A frontier model writes the script and the on‑screen visuals as real code; a TTS engine narrates; a deterministic renderer (Remotion) produces the MP4. Think "NotebookLM Video Overviews, but the visuals are real typeset math, real extracted figures, and purpose‑built animated diagrams instead of generic stock‑slide filler."

**The hypothesis under test (this was an explicit learning project, not a product build):**
> Can a frontier model produce *coherent freeform visuals* for an arbitrary paper — choosing per‑scene what belongs on screen (a figure, a typeset equation, a bullet, a custom animation) — rather than filling fixed slide templates?

**Answer from the MVP: yes, convincingly — with caveats (see A2/A7).** The model authored 12 distinct, conceptually‑correct animated scenes for *Attention Is All You Need* with no template system, and they hang together as a real explainer.

## A2. What the MVP proved (and didn't)

**Proved:**
- Deterministic rendering of model‑authored freeform visuals yields a coherent ~3‑minute explainer. Output: `paper_explainer.mp4` (1920×1080, 184.6 s, 16.4 MB).
- The two riskiest dependencies (local TTS + headless renderer) install and run on this machine with no GPU.
- Scene‑level timing (size each scene to its narration audio duration) is enough to avoid dead air / desync at the scene granularity. No forced alignment needed for a watchable result.
- A cheap "render one still per scene, eyeball it" validation loop catches layout/compile errors before paying for a full render. **Keep this pattern.**

**Did NOT prove / confounded:**
- **Generalization to arbitrary papers.** We tested on ONE paper that the authoring model knows extremely well from pretraining. Coherence is inflated by that familiarity. The figure‑identity and factual‑accuracy risks are much larger for out‑of‑distribution papers.
- **An autonomous LLM pipeline.** The "Opus, medium‑effort" steps (scene plan + Remotion code) were performed by the *interactive session model writing files directly*, **not** by a programmatic API call inside the pipeline. For a product this must become a real, grounded model call (with the figures actually shown to the model). This is the single biggest gap between MVP and v1.
- **Math/figure extraction quality.** Equations were hand‑written HTML/CSS because the model already knew them; figure extraction only caught embedded raster images and silently dropped vector figures. Neither is acceptable for v1 (see A7, Part D‑1/D‑2).

## A3. Exact stack & versions (verified on this machine)

| Component | Version / detail |
|---|---|
| OS | Linux 6.17 (Ubuntu‑family), 12 logical CPUs, no GPU used |
| Python | 3.13.9 (miniconda); project uses a venv at `paper2video/.venv` |
| Node | v24.14.0, npm 11.9.0 |
| ffmpeg | 6.1.1 |
| **PyMuPDF (`fitz`)** | 1.27.2 — PDF parse, page→PNG, embedded image extraction |
| **Supertonic** | 1.3.1 — local TTS, **ONNX runtime (onnxruntime 1.26.0), NO PyTorch**, ~35 MB of deps |
| **Remotion** | 4.0.469 + React 19 — deterministic React→MP4 renderer (headless Chromium) |
| Input PDF | `/home/soham/Downloads/attention_is_all_you_need.pdf` (15 pages, 2.2 MB) |

Performance observed (CPU‑only, 12 cores):
- TTS: ~5 s of compute per ~15 s of audio (≈3× real‑time synth).
- Render: 5537 frames @ 1080p in **211 s** (≈26 fps throughput, ≈1.1× real‑time). First render also downloads a headless‑Chromium shell (one‑time).

## A4. Current repo layout, file by file

```
paper2video/                      # → rename to paperview/ for v1
├── .venv/                        # python venv (supertonic, pymupdf, soundfile, numpy)
├── parse.py                      # STAGE 2: PyMuPDF parse → parsed.json + assets/*.png
├── parsed.json                   # per-page {page, n_chars, text, page_png, figures[]}
├── scenes.json                   # STAGE 3: the scene plan (12 scenes) — HAND-AUTHORED BY MODEL
├── tts.py                        # STAGE 4: Supertonic synth → audio/*.wav + durations.json
├── durations.json                # [{id, file, duration}] per scene (seconds)
├── assets/                       # page_1..15.png (full-page renders) + fig_p3_128.png,
│                                 #   fig_p4_182.png, fig_p4_183.png (3 extracted figures)
├── audio/                        # scene1..12.wav (44.1kHz mono) + _envtest.wav
├── paper_explainer.mp4           # FINAL deliverable (copy of remotion/out/paper.mp4)
└── remotion/                     # STAGE 5/6: the Remotion project
    ├── package.json              # remotion@4.0.469, @remotion/cli, react@19
    ├── tsconfig.json             # resolveJsonModule=true (needed to import durations.json)
    ├── public/                   # assets served to the renderer via staticFile()
    │   ├── audio/scene*.wav       #   (copied from ../../audio)
    │   └── assets/fig_*.png        #   (copied figures only; page renders not used)
    ├── out/                      # paper.mp4 + stills/s1..s12.png (validation stills)
    └── src/
        ├── index.ts              # registerRoot(RemotionRoot)
        ├── Root.tsx              # <Composition id="Paper" 1920x1080 fps=30 durationInFrames=Σ>
        ├── PaperVideo.tsx        # master timeline: lays scenes back-to-back as <Sequence>s
        ├── durations.json        # copy of ../durations.json (build-time import)
        ├── theme.tsx             # palette, fonts, Background (attention-graph), Card, math helpers
        └── scenes.tsx            # the 12 freeform scene components + SCENES registry
```

**Key contract today:** `PaperVideo.tsx` reads `durations.json`, and for each scene computes
`durationInFrames = ceil(duration * 30)`, wraps `<SceneN audio="audio/sceneN.wav" />` in a
`<Sequence from={cumulativeOffset} durationInFrames=...>`. Each scene component renders its own
`<Audio src={staticFile(audio)} />` plus freeform visuals. The scene id → component mapping lives in
the `SCENES` registry at the bottom of `scenes.tsx`.

## A5. The 6‑stage pipeline as built

All paths hardcoded (MVP). Run from `paper2video/` with the venv active (`source .venv/bin/activate`).

1. **Environment check (one‑time).** Confirmed Supertonic synth + Remotion hello‑world render both work before building anything. (Good discipline — the two scariest deps validated first.)
2. **Parse** — `python parse.py`
   - `doc.get_text("text")` per page; `page.get_pixmap(matrix=fitz.Matrix(2,2))` → `assets/page_N.png` (≈144 dpi); `page.get_images(full=True)` + `fitz.Pixmap(doc, xref)` → `assets/fig_pX_xref.png` (skips <80 px, converts CMYK→RGB). Writes `parsed.json`.
   - **Result:** 15 pages, **3** embedded figures (Fig 1 architecture p3; Fig 2 left/right p4). Vector‑drawn figures on pp.13–15 produced **no** embedded images and were silently skipped.
3. **Scene plan** — `scenes.json` (12 scenes). Each = `{ id, narration (1–3 sentences), visual_intent (free text) }`. **Authored directly by the model**, grounded in the abstract + extracted text + a visual look at the 3 figures. No fixed templates; `visual_intent` is open‑ended (e.g. "typeset softmax(QKᵀ/√dₖ)V, reveal term‑by‑term, with Fig 2‑left on a white card").
4. **TTS** — `python tts.py`
   - `TTS()` (model `supertonic-3`), `tts.get_voice_style("M2")`, `tts.synthesize(text, style, speed=1.0)` → `(wav[1,N] float32, lengths)`; `tts.save_audio(wav, path)`; duration via `soundfile.info(path).duration`.
   - **Result:** 12 WAVs, 12.6–20.6 s each, **184.4 s** total narration → `durations.json`.
5. **Composition** — the Remotion `.tsx` files (`theme.tsx`, `scenes.tsx`, `PaperVideo.tsx`, `Root.tsx`). 12 bespoke animated React components, **authored directly by the model**. Reusable primitives used ad hoc: `Background` (drifting attention graph), `Card` (white card for transparent figure PNGs), `Frac/Sub/Sup` (hand‑rolled math), `WordChip`, `DBox`.
6. **Render** — `npx remotion render src/index.ts Paper out/paper.mp4`
   - Validation first: `npx remotion still src/index.ts Paper out/stills/sN.png --frame=<midpoint>` for each scene; inspect; then full render. Printed wall time.

## A6. Critical technical learnings & API quirks (save the next agent hours)

**Supertonic**
- `pip install supertonic` pulls onnxruntime + soundfile + huggingface‑hub; **no torch**. Great for cheap/local/offline scale.
- First run auto‑downloads the model from HF (26 files). Models: `supertonic`, `supertonic-2`, `supertonic-3` (default). 10 voices: `F1–F5`, `M1–M5`. Sample rate **44100 Hz**, mono.
- API: `TTS().synthesize(text, voice_style, total_steps=8, speed=1.05, ...) -> (wav[1,N] float32, lengths[1])`. Squeeze to 1‑D before saving. Get duration from the saved WAV (`soundfile.info`).
- Also ships a CLI (`supertonic tts 'text' -o out.wav`) and an HTTP server (`supertonic serve`, exposes `/v1/tts` and an OpenAI‑compatible `/v1/audio/speech`). The server is handy for a language‑agnostic TTS microservice.

**PyMuPDF**
- `page.get_text("text")` is plain text only — **math becomes garbled/unicode soup; there is no LaTeX here.** Do not rely on it for equations.
- `page.get_images(full=True)` only returns *embedded raster* xrefs. **Vector figures (most modern paper diagrams!) are invisible to it.** This is why pp.13–15 figures were dropped. To capture vector figures you must detect the figure bbox and clip‑render the page (`page.get_pixmap(clip=rect)`), or use a dedicated figure extractor (Part D‑2).
- Caption/section structure is recoverable from text‑block bboxes (`page.get_text("dict")`), but it's fiddly; prefer GROBID / a layout model for v1.

**Remotion**
- Render entry is `src/index.ts` (calls `registerRoot`). One `<Composition id=...>` per video; `durationInFrames` must be an integer ≥ all sequence ends.
- Runtime assets (audio, images) must live under `remotion/public/` and be referenced with `staticFile("audio/x.wav")`. We **copy** `audio/` and figure PNGs into `public/` as a glue step.
- Build‑time data (`durations.json`) is `import`ed; needs `"resolveJsonModule": true` in tsconfig.
- `useCurrentFrame()` inside a `<Sequence>` is **local** to that sequence (starts at 0) — this is what makes per‑scene animation code simple. `<Audio>` inside the sequence likewise plays from the sequence start.
- Render is deterministic given identical inputs (good for tests). It runs generated React in headless Chromium — **this is an arbitrary‑code‑execution surface** (see Part D‑6 security).
- We used system fonts (`system-ui`). For reproducible/branded output, bundle fonts (`@remotion/google-fonts` or local files).

**Math rendering**
- We hand‑built equations with spans + a CSS fraction. It looked fine for 2 equations and the scaled‑dot‑product line wrapped to 2 lines (still legible). **This does not generalize.** v1 must render real LaTeX with **KaTeX** (deterministic, fast) inside Remotion (Part D‑4).

## A7. Honest limitations discovered (where it breaks)

1. **The "model" steps were a human‑in‑the‑loop interactive model, not a pipeline call.** Productizing means a real, grounded, *vision‑enabled* model call. Highest‑priority gap.
2. **Figure identity problem.** The composition step received only figure *filenames* + free‑text intent. The model "knew" which file was which because it *looked at them in the session*. An autonomous pipeline must feed the figures (as images) + their captions to the planner/composer. Otherwise it will mis‑place or hallucinate figures.
3. **Vector figures silently dropped** (PyMuPDF limitation above). For many papers the most important diagram won't be a raster image.
4. **No real math extraction.** PyMuPDF text mangles equations; we sidestepped it by hand. Arbitrary papers need a math‑aware extractor (arXiv source first; Nougat/Marker/Surya as open‑source OCR fallback) → LaTeX → KaTeX.
5. **Scene‑level timing only.** Within a scene, animation cues (e.g. "highlight the softmax term at frame 80") are hand‑guessed and **not** aligned to the spoken words, so emphasis drifts. Acceptable for MVP; for polish use forced alignment.
6. **No graceful degradation.** Pipeline assumes everything succeeds. A figure that won't extract or an equation that won't parse must fall back (e.g. to a bullet) instead of crashing.
7. **Determinism is partial.** The *render* is deterministic; **TTS and the LLM are not** (sampling). For reproducible tests, fix seeds/temperature where possible and cache the scene plan + audio.
8. **No tables, no algorithms, no references/citations** handled. No code‑listing rendering. No multi‑figure layout logic.

## A8. How to reproduce the MVP from scratch

```bash
cd /home/soham/Documents/paper2video
python3 -m venv .venv && source .venv/bin/activate
pip install supertonic pymupdf soundfile
python parse.py                       # → parsed.json + assets/*
# scenes.json already exists (the scene plan); regenerate by re-prompting a model
python tts.py                         # → audio/*.wav + durations.json
cd remotion && npm install
# copy runtime assets into public/ (glue):
mkdir -p public/audio public/assets
cp ../audio/scene*.wav public/audio/
cp ../assets/fig_*.png public/assets/
cp ../durations.json src/durations.json
# validate cheaply, then render:
npx remotion still  src/index.ts Paper out/stills/s7.png --frame=2998
npx remotion render src/index.ts Paper out/paper.mp4
```

---

# Part B — V1 vision & scope

**Rename:** repo/project → **`paperview`**. **Claude Code plugin named `ppv`** with command/skill `gen` → invoked as **`/ppv:gen`** (plugin name and repo name are independent; namespacing gives the clean `ppv:gen`). OpenCode gives a bare `/ppv` natively. *(Resolved — was Open Decision #1.)*

**Separate repo for testing:** the automated generate‑and‑judge harness lives in its **own repo, `paperview-judge-pipeline`** (depends on `paperview/core`), to keep heavy corpus/eval infra out of the product repo. See Part D‑10.

**Positioning / why this can win vs NotebookLM Video Overviews:**
- NotebookLM produces talking‑head/stock‑slide style video; it does **not** render the paper's *actual* math, figures, or bespoke diagrams. **Our wedge is fidelity:** real typeset LaTeX, the paper's real figures, and purpose‑built animated explanations of *that* paper's ideas. **→ LaTeX/figure extraction quality is the core differentiator and must be excellent (Part D‑1, D‑2). The user explicitly called this the selling point.**
- We live **inside the coding agent** the user already uses. Zero new app. The agent can explain a paper, a codebase, or even *its own decision* as a short video, in‑context.
- Local/cheap path (Supertonic + CPU Remotion) means we can run at scale for testing and offer a free tier.

**V1 surface:** a coding‑agent plugin. **Claude Code first**, **OpenCode second**. Repo holds a source‑agnostic **core** plus a thin **adapter per agent**.

**V1 scope recommendation (opinionated):** ship **papers only**, but architect the core to be **source‑agnostic** so codebase/decision modes slot in later (Part D‑9). Optionally include the near‑free "explain the agent's last decision" mode as a stretch demo.

## B1. Launch readiness & positioning (HN / Reddit GTM)

Context: closest comparable is `prajwal-y/video_explainer` (~178★, stale ~3 mo, **ElevenLabs‑based = paid + non‑local**). Read: interest is validated, **no dominant OSS incumbent**, clear differentiation axis — but the category's OSS‑star ceiling is modest, so a strong front‑page Show HN is *achievable, not guaranteed*, and is **demo‑ and timing‑dependent**.

- **Differentiation (lead with this combo):** *the paper's real LaTeX + real figures, rendered deterministically (not generative slop), 100% local, $0/video.* The explicit foil is **NotebookLM** ("talking head over generic slides" vs "we render the actual equations and figures"). Show a side‑by‑side on the same paper.
- **Supertonic is a *supporting* selling point, not the hero.** It powers the "local & free" story (strong on HN); the actual moat is visual fidelity + correctness. Don't headline the voice. Be ready for "sounds robotic vs ElevenLabs."
- **Lead the launch with the Claude Code plugin (decision).** For the actual ICP — already Claude Code users — the plugin is the **lower‑friction** path, not the higher one: it **inherits Claude Code's auth (no API key to acquire / no card / no per‑call cost)** and uses the user's **SOTA model at no marginal cost** → best setup *and* best output. The CLI's hidden cost is exactly the API key the plugin avoids. **But keep a thin standalone CLI as a fallback/repro path** (nearly free from `core + adapters`): it lets non‑agent users + the HN demo gallery reproduce results and neutralizes "why is it locked to one vendor?" — plugin is the hero, CLI is the safety valve. Not plugin‑*only*.
- **The plugin removes *API‑key* friction, not *local‑toolchain* friction.** First run still stands up the local stack: Python venv + PyMuPDF/Supertonic, Node + Remotion, ffmpeg, the headless‑Chromium shell, the Supertonic model download. So it's "zero *auth* setup," not "zero setup." **Nail the first‑run bootstrap** (auto‑install or a `/ppv:setup` step that provisions the toolchain) — that, not keys, is now the make‑or‑break setup story; get it wrong and the "best experience" promise breaks on install, not output.
- **#1 launch risk = launching too early.** HN/Reddit will instantly run it on *their* messy, non‑arXiv, math‑heavy paper and post the failure. The MVP's known weakness (great on memorized papers, degrades on arbitrary ones) is exactly that stress test. **Gate:** pick 10 *never‑tested* papers, render them, ask "would I be proud of all 10 on the front page?" — this is precisely what the judge pipeline (D10) is for. Ship a **gallery of 5+ diverse papers** (not just *Attention*) to preempt "only works on the one it memorized."
- **Correctness is existential for an educational tool.** A confidently‑wrong narration is worse than nothing and r/MachineLearning will catch it → grounding/faithfulness (D3) is launch‑blocking, not polish.
- **Reddit (plugin‑led):** primary = **r/ClaudeAI & r/Anthropic** (tight audience match with the plugin), secondary = **r/LocalLLaMA** (local‑TTS / $0 angle), then r/artificial. Open with r/MachineLearning only once correctness is bulletproof.
- **Founder thread engagement matters on HN** — be online to answer failure cases gracefully the day you post.
- **Manage expectations:** HN traction ≠ users ≠ product. Realistic good outcome = hundreds–low‑thousands of stars *if* the demo is strong and it works on arbitrary papers; viral is possible but contingent.

---

# Part C — Target architecture

## C1. Source‑agnostic core (the reusable engine)

```
                 ┌─────────────┐   scene plan    ┌──────────┐  wav+dur  ┌───────────┐   mp4
  source ──▶ INGESTER ──▶ assets+facts ──▶ PLANNER(LLM) ──▶ TTS ──▶ COMPOSER(LLM) ──▶ RENDERER ──▶ video
                 └─────────────┘  (JSON)          └──────────┘           └───────────┘
```

- **Ingester** (per source type): PDF/paper, codebase, diff/decision. Emits a normalized **`SourceBundle`**: `{ text_sections[], equations[](LaTeX), figures[]{file,caption,bbox,page,type}, tables[], metadata }`.
- **Planner** (LLM, vision): `SourceBundle` + controls (length, depth, audience, aspect) → **scene plan** (versioned JSON schema, C2). Must *see* the figures.
- **TTS**: scene narration → per‑scene audio + measured duration. Pluggable (Supertonic default; ElevenLabs/Kokoro/Piper optional).
- **Composer** (LLM): scene plan + asset manifest + per‑scene durations → Remotion composition, assembled from a **visual component library** with a constrained freeform escape hatch (C3).
- **Renderer**: Remotion → MP4 (+ optional SRT, thumbnail, vertical cut).

Everything between Ingester and Renderer is **source‑agnostic**. Only the Ingester is per‑domain. This is why generalizing beyond papers is mostly free (Part D‑9).

## C2. The scene‑plan contract (versioned)

Formalize what was `scenes.json` into a versioned JSON Schema shared by planner, composer, and the test harness. Proposed v1:

```jsonc
{
  "schema": "ppv.sceneplan/1",
  "meta": { "title": "...", "source": "attention_is_all_you_need.pdf",
            "target_seconds": 180, "aspect": "16:9", "voice": "M2", "audience": "intro" },
  "scenes": [
    {
      "id": 1,
      "narration": "1–3 sentences (this is the spoken script; TTS uses it verbatim).",
      "visual_intent": "free-text description of what's on screen",
      "assets": ["assets/fig_p3_128.png"],          // figures this scene references
      "equations": ["\\mathrm{softmax}(QK^T/\\sqrt{d_k})V"],  // LaTeX, if any
      "suggested_components": ["FigureCard", "EquationReveal"], // hint for composer
      "emphasis": [{ "term": "softmax", "when": "auto" }]       // for word-sync (later)
    }
  ]
}
```

## C3. Hybrid visual system (reliability + safety, without killing creativity)

The MVP's "fully freeform model‑written TSX" is creative but (a) risky to run (arbitrary code) and (b) unreliable on unfamiliar papers. Recommended v1 design: a **library of reusable, tested visual primitives** the composer *assembles*, plus a **sandboxed freeform escape hatch** for the rare custom diagram.

Seed the library from the MVP's already‑working scenes:
`TitleCard`, `FigureCard` (transparent PNG on white card), `EquationReveal` (KaTeX, term‑by‑term), `BulletReveal`, `DiagramStack`/`DBox` (boxes + arrows + Add&Norm‑style wrappers), `ComparisonTable`, `StatCallout` (count‑up numbers), `AttentionGraph` (all‑to‑all edges), `Waveform` (sinusoids), `SequenceHighlight` (word chips lighting up), `BackgroundGraph`, `Transition`.

This directly fixes A7‑1/2/6: the composer picks components and passes data; truly novel visuals use a constrained, linted, typechecked freeform block.

## C4. Proposed monorepo layout (matches the user's "core + a folder per agent")

```
paperview/
├── core/                         # source-agnostic engine (the reusable bit)
│   ├── ingest/                   #   paper/ (pdf), codebase/, decision/  ← Ingesters
│   ├── plan/                     #   planner prompts + scene-plan schema + validation
│   ├── tts/                      #   pluggable TTS (supertonic default, server adapter)
│   ├── compose/                  #   composer prompts + component library (Remotion)
│   │   └── components/           #   the visual primitive library (C3)
│   ├── render/                   #   remotion project + render driver
│   ├── cache/                    #   content-hash cache + build manifest
│   └── cli/                      #   `ppv` CLI: ppv gen <input> [--seconds --aspect --voice ...]
├── adapters/
│   ├── claude-code/              #   Claude Code plugin (name "ppv"): .claude-plugin/plugin.json,
│   │                             #     skills/gen/SKILL.md → /ppv:gen
│   └── opencode/                 #   OpenCode plugin (.opencode/plugins) + command (commands/ppv.md → /ppv)
├── examples/                     #   sample outputs
└── PAPERVIEW_V1.md               #   this doc

# SEPARATE REPO (not in paperview/):
paperview-judge-pipeline/         # automated generate+judge harness (Part D-10)
├── corpus/                       #   curated arXiv papers
├── run/                          #   batch runner (NIM backend, job queue, backoff)
├── judge/                        #   hard gates + VLM-as-judge + faithfulness checks
└── experiments/                  #   A/B configs + reports  (depends on paperview/core)
```

Both adapters are **thin**: they collect inputs + controls from the agent, shell out to / call the `core` CLI, stream progress, and hand back the MP4 path. All real logic stays in `core`.

## C5. Interaction model — how the user invokes `/ppv:gen`

**Recommendation: source‑required‑but‑flexible + optional natural‑language steering, with a cheap preview/confirm checkpoint before the expensive render.** We're inside a conversational coding agent — don't force rigid flags; let the agent interpret intent.

- **Invocation — one free‑form prompt, no flags (decision):** `/ppv:gen <natural‑language prompt>` carrying everything — the source (file path / arXiv id‑URL / context reference like "the paper we discussed", "the decision you just made", "this codebase") **plus** any of length, focus, aspect, resolution, voice, audience, in prose. **Claude parses the prose into the structured core‑API params** (trivial + low‑risk for simple knobs); omitted fields get sensible defaults; explicit values honored if written. List the controllable knobs in the command's **help text** for discoverability (the one thing flags gave for free).
  - **Echo‑back makes flag‑free safe:** before the expensive run, the agent shows its parsed interpretation (*"paper = X.pdf · ~3 min · focus = multi‑head attention · 1080p — go?"*) — this is the **preview checkpoint** below, doing double duty as parse‑confirmation; catches a misparsed "5 min" or wrong file.
  - **Keep a structured core API *underneath* the prose layer:** prose is the *human* front‑end; the `core` CLI's canonical interface stays **explicit/structured params**. The OpenCode adapter, the batch/judge harness, and reproducibility call the structured API directly — never make an LLM re‑parse prose across 40 papers × N variants (drift would pollute the A/B signal). **Prose on top, structured contract underneath.**
  - **The one failure‑prone parse is the *source*** (resolve a path / arXiv id / "this paper"): ambiguous (several PDFs in dir) → **ask, don't guess**. Knobs get safe defaults; artifact resolution is the part to handle carefully.
- **Preview checkpoint (important):** generation + render takes minutes. Before the expensive render, the agent shows the interpreted controls + the scene‑plan outline (optionally one still per scene — the MVP's cheap‑validation pattern). User approves/edits → render. Offer a `--yolo`/auto mode to skip the checkpoint.
- **Context‑as‑source unlocks generalization (D9) for free:** when source = "your last decision" / "this codebase", there's no external artifact — the agent's conversation context *is* the `SourceBundle`. Same command, no ingester. This is the cheapest and most differentiated interaction, so let it shape the command design **now**, even though only papers ship in v1.
- **Output:** the agent reports the MP4 path + render time/cost (as the MVP did) and can open/preview it.

---

# Part D — V1 workstreams

Each: **Goal · Why · Approach · Risks · Effort (S/M/L)**. Roughly priority‑ordered.

## D1. LaTeX & math extraction — *the differentiator* · Effort: **L**
- **Goal:** recover real LaTeX for every equation (display + inline) and feed it to KaTeX.
- **Why:** this is the explicit selling point over NotebookLM. The MVP cheated (hand‑written math).
- **Approach (tiered, best‑source‑first):**
  1. **arXiv source tarball** when available — the gold path. Map PDF → arXiv id (title search via arXiv API, or DOI/metadata), download LaTeX source from `https://arxiv.org/e-print/<id>`, parse `.tex` for equations, figure captions, section structure. **Perfect** equations, no OCR. Covers a huge fraction of ML/CS papers. *Prioritize this.*
  2. **Math OCR fallback** for non‑arXiv / scanned PDFs — **open‑source only, no paid APIs (decision: no Mathpix):** **Nougat** (Meta, PDF→Markdown+LaTeX), **Marker** + **texify**/**Surya** (VikParuchuri; fast, good, self‑hosted), **pix2tex / LaTeX‑OCR** (per‑equation). All run locally/free, consistent with the v1 "no paid services" constraint. *(Resolved — was Open Decision #3.)*
  3. **Structure/refs:** **GROBID** for sections, titles, references.
- **Render:** **KaTeX** in Remotion (bundle `katex` + its CSS; render to HTML in a component). Deterministic and fast. Build an `EquationReveal` component with term‑by‑term highlight.
- **Risks:** PDF→arXiv id mapping is fuzzy (title collisions); OCR latency/quality on dense math; KaTeX doesn't support 100% of LaTeX (have a fallback to an image render via MathJax/SVG).

## D2. Robust figure & table extraction · Effort: **M/L**
- **Goal:** capture *all* figures (raster **and** vector) + their captions; basic table handling.
- **Why:** MVP dropped vector figures (the common case). Figures are half the value.
- **Approach:**
  - Use a scholarly figure extractor: **pdffigures2** (AllenAI; figures+captions+regions) or **Marker/Surya** layout detection. Fallback: detect "Figure N:" caption blocks via PyMuPDF text bboxes, infer the figure rect, and **clip‑render** it (`page.get_pixmap(clip=rect, matrix=2x)`) — this captures vector figures the embedded‑image API misses.
  - Produce a **figure manifest**: `{file, caption, page, bbox, kind: photo|diagram|plot|table}`. The planner/composer consume captions + the images themselves (vision).
  - Tables → render as image crops for v1; structured table parsing later.
- **Risks:** layout models add heavy deps/latency; caption association errors; multi‑panel figures.

## D3. Real model‑driven, *grounded*, vision‑enabled planning + composition · Effort: **L**
- **Goal:** replace the human‑in‑the‑loop authoring with programmatic LLM calls that actually *see* the figures and are grounded in extracted text/LaTeX.
- **Why:** the core productization gap (A7‑1/2). Without vision, figure placement and factual accuracy degrade badly on unfamiliar papers.
- **Approach:**
  - **Planner call:** system prompt + `SourceBundle` (text/LaTeX + figure manifest + figure images inline) + controls → scene plan JSON (validated against C2 schema; retry on invalid). Temperature low for reproducibility.
  - **Grounding / anti‑hallucination:** require each factual claim in narration to be supported by extracted text; optionally a verification pass (RAG check: does narration match the source?). Cite page/section in the plan for auditability.
  - **Composer call:** scene plan + component‑library API docs + asset manifest + per‑scene durations → composition that *assembles components* (C3), freeform only as escape hatch.
  - In the **Claude Code adapter**, the agent's own (frontier) model is the planner/composer — no extra API key, best quality. The **judge pipeline** uses **NIM** (Part D‑10). The standalone `core` CLI keeps the LLM backend configurable so either can plug in.
- **Risks:** hallucinated claims; figure misattribution; JSON‑schema adherence; cost/latency of vision calls on many figures.

## D4. Visual component library + KaTeX · Effort: **M**
- **Goal:** harvest the MVP's 12 scenes into ~12–15 reusable, prop‑driven, tested components (C3) and add KaTeX.
- **Why:** reliability, safety, speed, and consistent look. Most of this code already exists in `scenes.tsx`/`theme.tsx` — it just needs to be parameterized.
- **Risks:** over‑abstracting (lose the freeform creativity that made the MVP good) — keep the escape hatch. The exact **freeform‑vs‑component‑library balance is decided empirically via A/B in the judge pipeline (D10), not a priori** (Resolved, was Open Decision #4).

## D5. Length / format / voice / depth controls · Effort: **S/M**
- **Goal:** user‑controllable knobs. The user asked for length control + "other aspects."
- **Controls:** `--seconds` (target duration → planner targets a scene count & per‑scene word budget; TTS durations finalize timing), `--aspect` (16:9 / 9:16 vertical / 1:1), `--voice` (**Supertonic F1–F5/M1–M5 only — v1 ships Supertonic, no premium/paid voices; Resolved, was Open Decision #5**), `--depth/audience` (intro vs expert; intuition‑heavy vs math‑heavy), `--resolution`, `--theme` (light/dark/brand), `--captions on/off`, `--music on/off`.
- **Implementation:** controls feed the planner prompt (scene count/depth) and the Remotion `<Composition>` dims. Duration is *approximate* because TTS length varies — plan for it (e.g. ±15%).

## D6. Reliability & **security** (sandbox the generated code) · Effort: **M**
- **Goal:** never crash on an arbitrary paper; never execute unsafe generated code.
- **Security (important):** rendering composes/executes model‑generated React/TSX in Node + headless Chromium. That is an **arbitrary‑code‑execution surface** running on the user's machine. Mitigations: prefer the constrained component library over freeform; **typecheck + lint + AST‑whitelist** generated code before rendering (no `fs`/`net`/`process`/`child_process`, only the allowed imports); render in a container/sandbox; pin deps. Treat the freeform escape hatch as the highest‑risk path.
- **Reliability:** graceful fallbacks (figure won't extract → bullet; equation won't parse → image or plain text; scene render error → skip with a placeholder, don't abort the whole video). Validate the scene plan against the schema and **render one still per scene before the full render** (bake the MVP's manual check into the pipeline).

## D7. Caching, incremental rebuild, build manifest · Effort: **S/M**
- **Goal:** fast iteration ("tweak scene 5, re‑render only what changed").
- **Approach:** content‑hash cache for parse → plan → audio → render artifacts. A `manifest.json` per build (inputs, controls, scene plan, durations, render stats, cost/time) for debugging + the test harness. The MVP intentionally skipped all caching; v1 needs it for a good agent UX.

## D8. Plugin packaging · Effort: **M** (verified formats below)

### Claude Code adapter (`adapters/claude-code/`)
- Manifest: `.claude-plugin/plugin.json` → `{ "name": "ppv", "version": "...", "description": "...", "author": {...}, "homepage", "repository", "license" }`. **Plugin name is `ppv`** (this is what determines the command namespace), even though the repo is `paperview`.
- Command: plugins expose commands as **`skills/<name>/SKILL.md`** (preferred) or flat **`commands/<name>.md`**. **Both are namespaced** → invoked as `/<plugin-name>:<name>`. With plugin name `ppv` and command `gen`, this gives the clean **`/ppv:gen`**. `$ARGUMENTS` captures the rest of the line (source + free‑text steering, per C5).
- Other dirs (at plugin **root**, *not* inside `.claude-plugin/`): `agents/`, `hooks/hooks.json`, `.mcp.json` (bundle the core as an **MCP server** if we want tool‑style invocation), `bin/` (executables added to PATH — could ship the `ppv` CLI here), `settings.json`.
- Test locally: `claude --plugin-dir ./adapters/claude-code`; reload with `/reload-plugins`; validate with `claude plugin validate`.
- Distribute: a **marketplace** repo with `.claude-plugin/marketplace.json`; users `/plugin marketplace add <repo>` then `/plugin install ppv@<marketplace>`. Community marketplace: `anthropics/claude-plugins-community` (submit via claude.ai/settings/plugins/submit).
- **Design choice:** because rendering needs Python (PyMuPDF/Supertonic) + Node (Remotion), the command should invoke the `core` CLI (shipped via `bin/` or installed separately) rather than do work in‑prompt. The model does planning/composition; the CLI does parse/TTS/render.
- **First‑run bootstrap (now the priority setup story — plugin‑led launch, per B1):** the plugin inherits Claude Code auth (no API key), but still must stand up the local toolchain on first use — Python venv + PyMuPDF/Supertonic, Node + Remotion, ffmpeg, the headless‑Chromium shell, and the Supertonic model download. Provide a `/ppv:setup` (or auto‑bootstrap on first `/ppv:gen`) that provisions + health‑checks this, with clear progress and a cached/idempotent re‑run. This is the make‑or‑break onboarding step; treat it as a first‑class workstream, not an afterthought.
- **⚠️ Plugin‑cache file‑resolution constraint (shapes core↔adapter wiring):** on install, Claude Code **copies the plugin dir into `~/.claude/plugins/cache`**, so a plugin **cannot reference files outside its own directory** — `adapters/claude-code` **cannot reach `../core`** at runtime. So don't wire the adapter to `core` by relative path. Options: ship **`core` as an installable package** (pip/npm) the bootstrap installs, ship a **`core` CLI in the plugin's `bin/`** (added to PATH), or vendor it. (`bin/` + bootstrap is the natural fit.)
- **Publishing = a marketplace:** `.claude-plugin/marketplace.json` at the `paperview` repo root → `{ name:"paperview", owner, plugins:[{ name:"ppv", source:"./adapters/claude-code", description }] }`; push to GitHub; users `/plugin marketplace add <owner/repo>` then `/plugin install ppv@paperview`. Updates via `version` bump (or commit‑SHA) + `/plugin marketplace update`. Optional public listing: `claude plugin validate` → submit at claude.ai/settings/plugins/submit → installs as `ppv@claude-community`. Monorepo source can also be `git-subdir`. Refs: [plugins](https://code.claude.com/docs/en/plugins), [marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).

### OpenCode adapter (`adapters/opencode/`)
- Command: markdown in **`.opencode/commands/ppv.md`** (project) or `~/.config/opencode/commands/ppv.md` (global) → **`/ppv`** (OpenCode commands are **not** namespaced, so a bare `/ppv` works here). Frontmatter: `description`, `agent`, `model`, `subtask`. Supports `$ARGUMENTS`, `$1..$n`, and `` !`cmd` `` shell injection. *(Verify `commands/` vs `command/` against your OpenCode version.)*
- Plugin (if we need event hooks): JS/TS in `.opencode/plugins/` or an npm package referenced via the `plugin` property in `opencode.json`. Plugin fn receives `{ project, client, $ (Bun shell), directory, worktree }` and returns hooks (command/file/session/tool/etc. events). Bun shell `$` is convenient for invoking the `core` CLI.

## D9. Generalization beyond papers · Effort: **S to architect, M+ per new source**
- **The user's question — scope creep or trivial?** **Verdict:** the *render core is trivially generalizable* (it just consumes a scene plan); the *ingestion is the per‑domain work*. So **architect for it now (cheap), ship papers only.**
- Make the core consume a generic `SourceBundle` and a generic command target ("explain X"). Then:
  - **Codebase / architecture explainer:** new ingester that walks a repo, summarizes structure/decisions → `SourceBundle`. Reuses everything downstream.
  - **"Explain the decision the agent just made":** *near‑free* and possibly the **killer demo** — the agent already has the decision in conversation context, so it can emit a scene plan directly with **no ingestion step**. Great wedge; cheap to add. Consider including as a v1 stretch (`/ppv explain-last` or similar).
- **Recommendation:** v1 = papers (full) + optionally the "explain last decision" mode (because it's nearly free). Defer codebase/architecture ingesters to v1.x. Don't build generic ingesters speculatively, but **don't hard‑code "paper" assumptions into the planner/composer/renderer.**

## D10. Automated testing at scale — *the optimization flywheel* · **separate repo `paperview-judge-pipeline`** · Effort: **M/L**
- **Goal:** generate **and** auto‑judge videos across a paper corpus with **no human in the loop**, and use the scores to *drive design decisions* — not just QA. **Thesis (the user's): if we can test coherence at scale, we can make it really good, fast.**
- **What it is (and isn't) — read before over‑investing:** a **measurement instrument, not a quality engine.** It doesn't *make* videos good; it tells you *whether* they generalize and *which* changes helped. **Highest value = failure discovery** (which paper classes break → drives eng priorities → *is* the launch gate), then A/B tuning past the obvious‑bug phase, then regression guarding. **Limits:** only as good as the judge (optimizing a weak judge → Goodhart; sanity‑check rankings against your own eyes — calibration proves the cheap judge ≈ Claude, not that *Claude* ≈ human taste); it measures but never *generates* improvements; diminishing returns while the product is rough (watching 10 by hand beats a harness then); a creative artifact resists a single score. **Quality actually lives in:** extraction fidelity (D1/D2, verified directly — the real moat), frontier generation + prompts + component library, grounding, and taste — the harness *steers*, it isn't the source. **Sequencing:** get the core hand‑decent first; then start with the *cheap* version (run ~20 diverse papers, read the labeled failures = ~80% of the value); save the full multi‑provider A/B cascade for when there's a product worth fine‑tuning.
- **Repo:** separate from the product (`paperview-judge-pipeline`), depends on `paperview/core` as a CLI/library.
- **LLM backends — one provider family per role (kills judge self‑preference bias structurally):**
  - **Generation:** NVIDIA **NIM** (bulk, `integrate.api.nvidia.com`, OpenAI‑compatible, 40 RPM / no daily cap, overnight) + **Claude** for winner regeneration. Backoff + a job queue; key/model rotation only if limits are per‑model.
  - **Judging:** **cross‑family, cheap, batched**, on **sampled stills + narration text (not the MP4)**, with **structured‑output JSON** for scores. Two complementary judges (ensemble, or start with the Fireworks one + Claude calibration):
    - OpenAI **GPT‑5.4‑mini** — *verified multimodal (text+image)*, 400K ctx, **Batch API + structured outputs supported**, **$0.75/$4.50 per M → batch $0.375/$2.25** (cached input $0.075). Best as the *reasoner* (narration‑vs‑source faithfulness). **Do NOT use GPT‑5.4‑nano for image judging — its vision support is unconfirmed.**
    - Fireworks **Qwen3‑VL 30B** (262K ctx, MoE = cheap/fast, "Thinking" variant for hard calls) — *primary VLM*; alt **Qwen2.5‑VL 72B** (max document/OCR/equation‑reading fidelity). Best as the *frame reader* (visual‑matches‑narration, equation legibility). ~**$0.5/$3 per M → batch ~$0.25/$1.50**. *(Avoid InternVL3 — 16K ctx too tight; Llama 4 — weaker on dense math/OCR.)*
    - GPT‑5.4‑mini is a *deliberately cheap* judge → that's why it's calibrated against Claude; if correlation is weak, step up to full GPT‑5.4 or Qwen3‑VL‑Thinking. Use the **synchronous** API (full price, pennies) for the CI smoke test (D10a). Verified June 2026 — re‑check pricing/specs before relying on exact numbers.
  - **Calibration:** **Claude** as gold judge on a **small stratified sample (~20–50), batched** — Spearman vs the cheap judges. **Hygiene: calibrate on the *same NIM‑generated set* the cheap judges scored; never put Claude‑*generated* videos in the correlation (Claude‑judging‑Claude reintroduces the bias).**
  - **Start lean:** one cheap judge + Claude calibration first; add the second judge only if single‑judge variance demands. Don't build four‑provider plumbing for ~$8.50 of credits.
- **Judge cost is a rounding error (not the bottleneck):** stills+text judging ≈ **$0.001–0.01/video** (batch 50% off). The blow‑up risk is image tokens → **downscale frames to ~768px / low‑detail, 1 frame/scene, one per‑video call.** Cents/night; small credits last weeks. **The constraint is generation throughput (NIM 40 RPM) for the stills‑only bulk, or full‑video render for the small motion/showcase subset — never judge cost.**
- **Render only what the judge needs — the big throughput lever (changes the "render is the wall" conclusion):** the judge needs **~1 still/scene + narration *text*, not the encoded MP4.** Stills render in *seconds* (sub‑second/frame once bundled) vs ~3.5 min for a full video. So **bulk content A/B = render ~12 stills (at full 1080p — cheap, crisp = judge reads equations better), skip the video encode**, and even **skip TTS** (narration text is what the judge compares against; TTS only matters for timing/pacing/audio). Render each still **near the scene's end** (fully‑revealed state), not midpoint. This makes the bulk loop **NIM‑generation‑bound (~hundreds/night, capped by 40 RPM), not render‑bound.**
- **Full‑video renders only for the subset that needs motion:** a small pacing/motion‑quality judge sample, winner‑confirmation, and showcase. For those, **batch at 720p24** (~2.5× faster than 1080p30, negligible effect on the judge since frames are downscaled to a fixed target anyway); **product + showcase stay 1080p30**. Periodically check that 720p rankings match 1080p on a small sample (a "render‑fidelity calibration," same logic as NIM→Claude).
- **Parallelization recap:** judging parallelizes for free (batch); NIM gen parallelizes to 40 RPM and overlaps with any rendering. With stills‑only bulk, the **single‑machine full‑video render ceiling (~100–150/night) no longer gates the bulk** — it only applies to the motion/showcase subset.
- **Throughput reality (important):** at **~5 min wall per video** (parse + TTS + ~3.5 min CPU render on one laptop), **render — not the 40 RPM limit — is the bottleneck.** A full gen+judge cycle is only ~5–15 NIM calls, so 40 RPM is plenty. Budget **~100–150 videos/night** on a single machine → run a *focused* corpus (e.g. 30–60 papers) with variants overnight, not thousands.
- **⚠️ Methodology caveat (do not skip):** the harness uses **cheap NIM open models** for generation, but the **product (Claude Code) uses a frontier model** as planner/composer. So **absolute** coherence scores here *understate* real product quality (the MVP's strong result came from a frontier model). **Relative A/B deltas should still transfer** — so **design on the deltas, not the absolute numbers**. Operationalized by the **backend cascade** below.
- **Backend cascade (cheap breadth → frontier depth on winners) — the recommended run strategy.** Orchestrate **OpenCode headless** as the batch harness: it drives *both* backends by swapping provider/model (NIM is OpenAI‑compatible; Anthropic provider for Claude), and running through OpenCode exercises the **real adapter path**, not a synthetic API call. Two **independent axes** — *generation backend* and *judge backend* — each NIM (bulk) or Claude (sprinkled):
  1. **Breadth:** generate every variant × paper with **NIM**; judge all with the **cheap cross‑family judges (OpenAI/Fireworks, batch)**. Overnight, **zero Claude quota** (Claude reserved for calibration + winners).
  2. **Calibrate the judge (small Claude‑judge budget):** re‑judge a **stratified** sample (top + middle + bottom of NIM's ranking) with Claude; compute **rank correlation (Spearman)** between NIM‑judge and Claude‑judge. High → trust NIM's rankings for the rest; low → NIM judge unreliable, widen the Claude sample. *This is what earns the right to trust the cheap rankings.*
  3. **Winners (Claude generation):** regenerate the winning **configs** (and the best **papers**) with Claude to (a) confirm the *config* ranking **transfers to frontier** — the real validity check, since the product ships on Claude — and (b) produce ceiling‑quality showcase outputs.
  - **Orchestration (background + sparse notify, *not* per‑iteration model supervision):** Claude Code can launch the batch runner as a **background task** (`run_in_background`, which re‑invokes the session on exit) and surface progress via a **Monitor** tailing the run log / **notification hooks** / **scheduled wake‑ups** — staying **idle (≈no token spend) in between**. So "background it and get pinged" is the right pattern. What to avoid is putting the **Claude model in the per‑video loop** (~100–150 wake‑ups/night = needless tokens+latency): wake the model only on **completion + failures/milestones**, not every render. **For a truly unattended run, detach the runner** (`nohup`/`systemd`/`tmux`) so it survives the session/terminal closing (a session‑bound background job may not); disable laptop sleep. Claude is invoked only for the sprinkled calibration/winner steps; keep the **Claude budget an explicit knob** (*N* calibration‑judges + *M* winner‑regens/night).
- **⚠️ Judge self‑preference bias:** largely solved **structurally** by the cross‑family split above (NIM/Claude generate; OpenAI/Fireworks judge). Residual care: it re‑appears in **calibration** (Claude judging Claude‑generated) — so keep the generation source constant there. General hygiene regardless: **blind the judge** to the generation backend, **randomize order**, and prefer **pairwise A/B ("which is better?" vs a frozen baseline)** over absolute 1–N scoring — more reliable for small/cheap judges and cheaper.
- **Corpus design — stratify against what breaks the pipeline, label everything, keep it small (papers only for v1):**
  - **Size:** ~30–60 papers (start ~20); with multiple variants/paper that's 1–2 nights. Don't build a 500‑paper set you can't iterate on.
  - **#1 axis — familiarity (the core confound):** mix *famous* papers the model knows cold (Attention, ResNet, BERT) with *obscure + recent post‑cutoff* papers it cannot have memorized. If it only works on famous ones, you see it here and nowhere else.
  - **Other axes to span:** math density (light ↔ heavy theory); **figure type** (raster ↔ **vector‑only** [MVP dropped these] ↔ figure‑light ↔ figure‑heavy); **source availability** (arXiv‑LaTeX‑source = gold path ↔ arXiv‑PDF‑only ↔ non‑arXiv ↔ scanned/old); field (cs.LG + physics/bio/econ/math — different notation/figure conventions); length (4pg ↔ 30pg+).
  - **Label every paper with its tags** → judge output becomes a *failure taxonomy by class* ("breaks on vector‑figure papers," "hallucinates on post‑cutoff theory"), not just an average.
  - **3–5 hand‑verified "golden" anchors** (a good explainer is known‑achievable) as a regression/sanity set. Don't let famous papers dominate (that trap flattered the MVP).
  - **Papers vs codebases:** **keep them separate** — different ingesters, failure modes, and judge rubrics; mixing muddies the signal and a config may help one source type and hurt the other. v1 ships papers → the scored corpus is papers only. Keep a *tiny separate non‑paper smoke set (~3–5 codebases) outside the scored corpus* to confirm the source‑agnostic core doesn't paper‑overfit (cheap insurance for D9). Codebases get their own labeled corpus + rubric in v1.x.
- **Judge (automatic):**
  1. **Hard gates:** parse OK · scene plan schema‑valid · audio synthesized · render completes without crash · A/V durations match.
  2. **VLM‑as‑judge** (a **NIM‑hosted vision model** — verify one is good enough; this is a quality risk): sample frames per scene + narration → score *visual‑matches‑narration / factual‑correctness‑vs‑source / readability / layout* (1–5 each), aggregate.
  3. **Faithfulness/RAG:** does narration align with extracted text/LaTeX (catch hallucinations)?
  4. **Equation/figure fidelity:** did claimed equations render? are referenced figures the right ones (caption match)?
  5. **Cost/latency** per stage.
- **A/B experiments to run here (the decisions we deferred):**
  - **freeform vs component‑library balance** (the actual deciding venue for that choice).
  - scene count / pacing / target‑duration presets.
  - narration style (intuition‑heavy vs precise) and audience presets.
  - planner/composer **prompt variants**.
  - figure **embed vs redraw** · captions on/off · transitions on/off.
  - which NIM model for gen vs which for judge.
- **Output:** per‑variant report — render success rate, mean coherence, failure taxonomy (by stage & paper class), cost/latency. This is the only way to actually validate the "arbitrary paper" hypothesis the MVP could **not** prove — and the loop that lets us improve quickly.

## D10a. CI: regression gate vs the overnight quality run (two different jobs) · Effort: **M**
- **Principle:** **CI = regression detection (deterministic, blocking). Overnight batch (D10) = quality measurement (stochastic, measured).** Don't gate merges on a fuzzy LLM coherence score — NIM generation + the VLM judge are stochastic, so a score threshold flakes and erodes trust. Tier the tests:
  - **Tier 1 — every PR, blocking, deterministic, no LLM/secrets:** freeze a known‑good scene plan (golden file) → TTS → render; assert mechanical invariants: render exits 0, valid MP4 with right dims/fps, audio present + non‑silent, total duration ≈ Σ scene durations, one still per scene renders. With the component library (D4), **golden‑test each visual primitive** in isolation. This is the real merge gate.
  - **Tier 2 — smoke, on `main`/nightly/manual dispatch, needs NIM secret:** real OpenCode+NIM generate → render → NIM‑judge on 1–2 fixed papers. **Hard gates block** (parse / schema‑valid plan / audio / render completes / A/V durations match); **coherence score is reported, not blocking** (PR comment / trend; fail only on regression vs a stored baseline beyond a generous margin). = one cell of the D10 cascade as a smoke test.
  - **Tier 3 — the corpus × variants cascade (D10) is NOT CI:** keep it on the laptop/self‑hosted runner (cost, render time, flakiness, quota).
- **CI gotchas:**
  - **Secrets + forks:** GitHub masks secrets on fork PRs → the NIM‑grading job runs only on your branches / manual dispatch. **Avoid `pull_request_target` + fork checkout** (secret‑exfiltration footgun).
  - **Render is slow on hosted runners** (~2–4 vCPU → ~15+ min vs 3.5 min on the 12‑core laptop). **Register the overnight laptop as a self‑hosted runner** so CI renders fast and the NIM key stays local.
  - **Cache big downloads:** Supertonic HF model (26 files) + Remotion headless‑Chromium shell via `actions/cache`, else every run re‑downloads.
  - **Cut variance:** temperature=0, fixed voice/seed; judge **pairwise vs a frozen baseline output** rather than absolute scoring — a far more stable CI signal.

## D11. Production polish (post‑core) · Effort: **S each**
- Scene **transitions** (`@remotion/transitions` — crossfade/slide instead of hard cuts).
- **Captions / SRT**: burned‑in subtitles + sidecar `.srt` (accessibility + engagement; also a NotebookLM gap). Pairs with forced alignment.
- **Word‑level sync** (optional): forced alignment (**WhisperX** / aeneas / Montreal Forced Aligner, or coarse timing from Supertonic chunk lengths) to drive word‑synced highlights/captions (fixes A7‑5).
- **Music/SFX bed** (royalty‑free), **thumbnail** generation, **vertical 9:16** auto‑cut for shorts.
- **Fonts** bundled for deterministic/branded output.

---

# Part E — Cross‑cutting concerns

- **Determinism caveat:** "deterministic rendering" refers to the *render*, not the whole pipeline. LLM + TTS are stochastic. For reproducible builds/tests, cache the scene plan + audio (content‑hash) and fix seeds/temperature where the backend allows.
- **Cost & latency budget:** track $ and wall‑time per video; the agent should report them (like the MVP printed render time). Vision calls over many figures dominate cost — cache aggressively.
- **Licensing / copyright (do not skip):** the MVP paper grants figure reproduction explicitly; **arbitrary papers may not.** Embedding copyrighted figures into a generated video is a real legal question. Options: redraw/abstract figures vs embed‑with‑citation; always cite source; possibly a setting. Get a position before public launch.
- **TTS:** **v1 ships Supertonic only** (fast/local/free — ideal for overnight scale testing, privacy, and a free tier; Resolved, was Open Decision #5). Keep the TTS interface pluggable so alternatives (Kokoro/Piper/XTTS local; premium) can be added in v1.x, but don't build them for v1.
- **Observability:** structured per‑stage logs + the `manifest.json` build record; essential for debugging arbitrary‑paper failures and for the test harness.

---

# Part F — Decisions

## Resolved (this round)
- **#1 Command name** → Claude Code plugin **named `ppv`**, command `gen` → **`/ppv:gen`** (clean namespace; repo stays `paperview`). OpenCode → bare `/ppv`.
- **#3 Math extraction** → **arXiv‑source‑first + open‑source OCR fallback only. No paid services (no Mathpix).**
- **#4 Freeform vs component‑library balance** → **decided empirically via A/B in the judge pipeline (D10),** not a priori. Ship a hybrid; let data pick the ratio.
- **#5 TTS** → **Supertonic only for v1** (interface stays pluggable for later).
- **Interaction model** → **one free‑form prompt, no flags** — `/ppv:gen <prose>` carries source + all knobs; Claude parses to the structured core‑API params; **echo‑back/preview checkpoint** confirms the parse before the run; **structured core API kept underneath** the prose layer for OpenCode/batch/repro (C5).
- **Testing infra** → **separate repo `paperview-judge-pipeline`**; **backend cascade, one family per role** — **generate** on NIM (+ Claude for winners), **judge** cross‑family + cheap + batched (OpenAI GPT‑5.4‑mini and/or Fireworks VLM, batch ~50% off), **calibrate** with Claude on a small sample. Orchestrated via **OpenCode headless**; Claude Code launches the runner as a **background task** and is **notified on completion/failures** (idle in between — keep the model out of the per‑render loop; detach the runner for unattended overnight runs). Start lean (one judge) — judge cost is cents/night. **Bulk content A/B renders stills only (no MP4/TTS) → generation‑bound, not render‑bound; full‑video render only for motion/showcase.**

## Still open (need the human)
- **#2 v1 source scope:** papers only, or papers + the near‑free "explain your last decision" mode? (Recommend: papers + decision mode *iff* it's truly cheap to wire — it reuses everything downstream of ingestion.)
- **#6 Figure copyright posture** (Part E): embed‑with‑citation vs redraw/abstract, before any public/shared output. (Could itself be an A/B in the judge pipeline for quality, but the *legal* call is human.)
- **#7 Distribution:** private/team marketplace first, or straight to the community marketplace (`anthropics/claude-plugins-community`)?
- **NIM model choice** for generation and for the VLM judge (verify a NIM vision model is good enough to judge figure/narration coherence).

---

# Part G — Suggested milestones / sequencing

- **M0 — Refactor MVP into `core` CLI.** Extract parse/plan/TTS/compose/render into `core/` with hardcoded‑paths removed; `ppv gen <pdf>` reproduces today's output. (Foundation for everything.)
- **M1 — Real grounded pipeline.** Programmatic vision‑enabled planner + composer (D3) + scene‑plan schema (C2). Now it runs end‑to‑end with *no human authoring*. Test on 3–5 *new* papers — this is the first real test of the hypothesis.
- **M2 — Differentiators.** LaTeX extraction (D1) + robust figures (D2) + KaTeX/component library (D4). Now it's actually better than NotebookLM on fidelity.
- **M3 — Controls + reliability + caching** (D5/D6/D7). Production‑grade enough to hand to users.
- **M4 — Claude Code plugin** (D8) → dogfood. Then **OpenCode adapter**.
- **M5 — Judge pipeline** (separate repo `paperview-judge-pipeline`, NIM‑only, D10) → measure coherence across a corpus, **A/B the deferred design decisions**, fix the worst failure classes. This is the flywheel — stand it up early (right after M1) so every later choice is data‑driven, not guessed.
- **M6 — Polish** (D11) + launch (marketplace).
- *(Stretch, cheap, any time after M1: the "explain the agent's last decision" mode, D9.)*

---

# Part H — References & links

- Claude Code plugins: https://code.claude.com/docs/en/plugins · reference: https://code.claude.com/docs/en/plugins-reference · marketplaces: https://code.claude.com/docs/en/plugin-marketplaces · discover/install: https://code.claude.com/docs/en/discover-plugins · community marketplace repo: `github.com/anthropics/claude-plugins-community`
- OpenCode: plugins https://opencode.ai/docs/plugins/ · commands https://opencode.ai/docs/commands/
- Remotion: https://www.remotion.dev · transitions `@remotion/transitions` · captions `@remotion/captions` · fonts `@remotion/google-fonts`
- KaTeX: https://katex.org
- Supertonic: `pip install supertonic` (ONNX TTS; HF model auto‑download; CLI + `serve` HTTP w/ OpenAI‑compatible endpoint)
- PyMuPDF: https://pymupdf.readthedocs.io
- Math/figure extraction (all open‑source — Mathpix and other paid APIs excluded from v1): Nougat (`facebookresearch/nougat`), Marker + Surya + texify (`VikParuchuri/marker`), pix2tex/LaTeX‑OCR, pdffigures2 (`allenai/pdffigures2`), GROBID
- arXiv source: `https://arxiv.org/e-print/<id>` ; arXiv API for title→id
- Forced alignment: WhisperX, aeneas, Montreal Forced Aligner
- Judge‑pipeline LLM backends (v1, one family per role): **generate** = NVIDIA NIM (`build.nvidia.com` / `integrate.api.nvidia.com`, OpenAI‑compatible, 40 RPM / no daily cap) + Claude (winners); **judge** (cross‑family, batch ~50% off) = OpenAI **GPT‑5.4‑mini** (multimodal text+image, $0.75/$4.50 per M, batch+structured outputs — [docs](https://developers.openai.com/api/docs/models/gpt-5.4-mini)) + Fireworks **Qwen3‑VL 30B** or **Qwen2.5‑VL 72B** (~$0.5/$3 per M — [models](https://fireworks.ai/models), [pricing](https://docs.fireworks.ai/serverless/pricing)); **calibrate** = Claude (small sample). NOT GPT‑5.4‑nano (vision unconfirmed). Orchestrated via **OpenCode headless** (`opencode run` — verify exact headless invocation). OpenRouter dropped for v1. *(Model facts verified June 2026.)*

---

# Appendix — exact versions, key commands, file inventory

**Versions:** Python 3.13.9 · Node v24.14.0 / npm 11.9.0 · ffmpeg 6.1.1 · PyMuPDF 1.27.2 · Supertonic 1.3.1 (model `supertonic-3`, 44100 Hz, voices F1–F5/M1–M5) · Remotion 4.0.469 · React 19.

**MVP numbers:** 15 pages parsed · 3 raster figures extracted (vector figures on pp.13–15 missed) · 12 scenes · 184.4 s narration · 5537 frames @ 1080p30 · render 211 s on 12 CPU cores · `paper_explainer.mp4` 16.4 MB.

**Key commands:**
```bash
# TTS quick test
python -c "from supertonic import TTS; t=TTS(); import soundfile as sf, numpy as np; \
w,_=t.synthesize('hello', t.get_voice_style('M2')); t.save_audio(np.asarray(w).squeeze(),'x.wav'); \
print(sf.info('x.wav').duration)"
# Remotion: list comps / still / render
npx remotion compositions src/index.ts
npx remotion still   src/index.ts Paper out/stills/sN.png --frame=<n>
npx remotion render  src/index.ts Paper out/paper.mp4
```

**The 12 MVP scenes (the proven narrative arc, reuse as a template):**
1 Title/hook · 2 RNN is sequential (bottleneck) · 3 Attention is all‑to‑all (parallel) · 4 Full architecture (real Fig 1) · 5 Inside one encoder layer (Add&Norm, residual, N=6, d_model=512) · 6 Q/K/V intuition · 7 Scaled dot‑product attention (equation + real Fig 2‑left) · 8 Multi‑head attention (real Fig 2‑right, h=8) · 9 Positional encoding (sinusoids + equation) · 10 Why self‑attention (complexity comparison) · 11 Results (28.4 / 41.8 BLEU, 3.5 days) · 12 Closing ("Attention is all you need.").

**Files to read first when resuming:** this doc → `remotion/src/scenes.tsx` (the freeform visual vocabulary that worked) → `remotion/src/PaperVideo.tsx` (the scene‑plan→timeline contract) → `parse.py` (ingestion + its limits) → `tts.py` (Supertonic usage).
