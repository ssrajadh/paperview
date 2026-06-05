# PaperView (`ppv`)

Turn a research-paper PDF into a narrated, animated explainer video — using **deterministic
rendering** (real typeset math + the paper's real figures, rendered with code), not generative
video. Runs **locally**: local TTS (Kokoro; or ElevenLabs for a cloud upgrade), local render
(Remotion). No API keys for the heavy lifting; the planning/composition is done by the coding
agent you already use.

> Status: **v1.** Claude Code adapter only.

## Layout

```
core/                  source-agnostic engine
  ppv/                 Python package + `ppv` CLI (ingest, tts, render, setup)
  remotion/            deterministic Remotion render project + component library
adapters/
  claude-code/         Claude Code plugin (name "ppv") → /ppv:setup, /ppv:gen
docs/                  design doc
examples/              sample scene plans / outputs
```

## How it works

```
PDF ──ppv parse──▶ text + figures ──[agent writes scene plan]──▶ scenes.json
        ──ppv tts──▶ audio + durations ──ppv render──▶ explainer.mp4
```

The **agent** (Claude Code) parses your request, looks at the extracted figures, and authors a
**scene plan** (narration + which visual component + props per scene). The **`ppv` CLI** does the
deterministic parts: PDF parsing, TTS, and rendering the scene plan through a fixed library of
animated React components.

## Quickstart (local dev)

```bash
# 1. load the plugin from this repo (no install/marketplace needed)
claude --plugin-dir ./adapters/claude-code

# 2. one-time toolchain bootstrap
/ppv:setup

# 3. make a video
/ppv:gen ~/Downloads/attention_is_all_you_need.pdf, 3 minutes, focus on attention
```

## CLI (what the agent drives)

```bash
ppv doctor                       # health-check the toolchain
ppv parse  <pdf|md|txt> --out <dir>    # text + figures (PDF, Markdown, or text source)
ppv validate <scenes.json> [--assets <dir>]   # fast-fail plan check (no TTS/render cost)
ppv tts    <scenes.json> --out <dir>   # narration WAVs + durations.json
ppv render <scenes.json> --workdir <dir> --out <mp4> [--resolution 810p|540p] [--draft] [--crf N] [--progress]
```

Run `ppv components` for the component library and `ppv schema` for the full plan JSON Schema
(`ppv tts --list-voices` lists the narration voices).
