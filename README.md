# PaperView (`ppv`)

Turn a research-paper PDF — **or a codebase** — into a narrated, animated explainer video, using
**deterministic rendering** (real typeset math, the paper's real figures, syntax-highlighted code,
and Mermaid diagrams rendered with code), not generative video. Runs **locally**: local TTS
(Kokoro), local render (Remotion). No API keys for the heavy lifting; the planning/composition is
done by the coding agent you already use.

> Status: **v0.1** (early — first public release). Claude Code adapter only.

## Layout

```
core/                  source-agnostic engine
  ppv/                 Python package + `ppv` CLI (ingest, tts, render, setup)
  remotion/            deterministic Remotion render project + component library
adapters/
  claude-code/         Claude Code plugin (name "ppv") → /ppv:setup, /ppv:gen
examples/              sample scene plans / outputs
```

## How it works

```
PDF / codebase ──parse or read──▶ text, figures, or source ──[agent writes scene plan]──▶ plan.json
                  ──ppv tts──▶ audio + durations ──ppv render──▶ <topic>.mp4
```

The **agent** (Claude Code) parses your request and reads the source — a paper's text and extracted
figures, or a codebase's source (cloned for you if you pass a GitHub URL) — then authors a **scene
plan** (narration + which visual component + props per scene). The **`ppv` CLI** does the
deterministic parts: PDF parsing, TTS, and rendering the scene plan through a fixed library of
animated React components. The output is named for the topic and lands in its own run directory
under `~/.paperview/runs/`.

## Quickstart

Prerequisites: [Claude Code](https://claude.com/claude-code), plus `git`, `python3`, `node`/`npm`,
and `ffmpeg` on your `PATH`. `/ppv:setup` installs everything else (Python venv, Remotion deps,
local models — and on Linux the headless-Chrome system libs the render needs).

Run these inside an interactive Claude Code session:

```bash
# 1. add the marketplace + install the plugin (one time)
/plugin marketplace add ssrajadh/paperview
/plugin install ppv@paperview
/reload-plugins                # activate the freshly installed /ppv: skills

# 2. one-time toolchain bootstrap
/ppv:setup

# 3a. make a video from a paper PDF
/ppv:gen ~/Downloads/attention_is_all_you_need.pdf, 3 minutes, focus on attention

# 3b. ...or from a codebase / GitHub URL (it clones the repo for you)
/ppv:gen https://github.com/owner/repo, 2 minutes, focus on the architecture
```

To update later, refresh the marketplace and reload — `/plugin marketplace update paperview`
then `/reload-plugins` (pulls the latest plugin; re-run `/ppv:setup` if a release changes the
toolchain).

<details>
<summary>Contributor / local-dev install (run straight from a clone, no marketplace)</summary>

```bash
git clone https://github.com/ssrajadh/paperview && cd paperview
claude --plugin-dir ./adapters/claude-code   # load the plugin from the working tree
/ppv:setup
/ppv:gen ~/Downloads/attention_is_all_you_need.pdf, 3 minutes, focus on attention
```
</details>

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

## License

PaperView itself is licensed under **Apache-2.0** (see [LICENSE](LICENSE)).

It builds on third-party tools that carry their **own** licenses, which govern what you may do
with the rendered pipeline — read them before any commercial or at-scale use:

- **Remotion** (rendering) is *source-available, not classic OSS*: free for individuals and small
  teams, but companies above its size threshold need a paid license, and there are restrictions on
  building competing products. See https://remotion.dev/license — PaperView's Apache-2.0 grant does
  **not** override these terms.
- **PyMuPDF** (PDF parsing) is **AGPL-3.0** (or a commercial license from Artifex). You install it as
  a dependency; obligations attach to anyone who redistributes a combined work.
- **Kokoro** (local TTS) ships Apache-2.0 weights.

**Privacy:** PaperView runs entirely locally and collects no data — no analytics, telemetry, or
phone-home. See [PRIVACY.md](PRIVACY.md).
