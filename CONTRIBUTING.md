# Contributing to PaperView

Thanks for your interest! PaperView is early (v0.1), so contributions — bug reports, fixes, tests, new visual components, parsing improvements, and adapters for other coding agents — are all welcome.

## How it's built (the 1-minute version)

PaperView is a **source-agnostic core** plus thin **agent adapters**:

```
core/
  ppv/         Python package + `ppv` CLI — ingest, math, tts, render, schema (deterministic)
  remotion/    Remotion render project + the component library (src/components/index.tsx)
adapters/
  claude-code/ the Claude Code plugin (skills: /ppv:setup, /ppv:gen)
examples/      sample scene plans
scripts/       setup.sh (toolchain bootstrap)
```

The split that matters: **the coding agent does the judgment** (reads the source, writes a
**scene plan**), and **the `ppv` CLI does the deterministic mechanics** (parse, TTS, render). A
scene plan is JSON — `{ "meta": {...}, "scenes": [ { "narration", "component", "props" }, ... ] }` —
validated against a fixed schema and rendered through a fixed library of React components. There is
no freeform display-code generation; adding a visual = adding a component to that library.

## Dev setup

```bash
git clone https://github.com/ssrajadh/paperview && cd paperview
claude --plugin-dir ./adapters/claude-code   # load the plugin from your working tree
/ppv:setup                                    # provisions the venv, Remotion deps, local models
```

`/ppv:setup` creates a virtualenv at `~/.paperview/venv`. For fast iteration you can drive the CLI
directly without going through the agent:

```bash
~/.paperview/venv/bin/ppv doctor              # health-check the toolchain
~/.paperview/venv/bin/ppv components           # list components + their props
~/.paperview/venv/bin/ppv schema               # full scene-plan JSON Schema
```

## The iteration loop (there's no formal test suite yet)

Verify changes by running the pipeline on a small plan — the cheap checks first:

```bash
ppv validate examples/<plan>.json --assets <assets-dir>   # props + TTS-symbol lint, no render cost
ppv preview  examples/<plan>.json --workdir /tmp/ppv --all # per-scene PNGs (fast, no TTS)
ppv render   examples/<plan>.json --workdir /tmp/ppv --out /tmp/out.mp4 --draft   # 810p@24fps, fast
```

`--draft` is the fast preset; re-render at `--resolution 1080p` only for a final check. Always
`ppv preview` dense scenes (equations, code, figures, tables) before a full render — clipped layouts
only show up when you look.

## Common contributions

**Add a visual component** (the main extension point):
1. Declare it in `core/ppv/schema.py` — add an entry to the `COMPONENTS` dict (its `required` /
   `optional` props and a one-line purpose). This is the contract `ppv validate` enforces.
2. Implement the React component in `core/remotion/src/components/index.tsx` and register it in the
   `REGISTRY` map at the bottom (keep it deterministic — no randomness, no network).
3. `ppv components` should now list it; add an example scene and `ppv preview` it.

**Add a TTS provider:** implement it in `core/ppv/providers.py` and add it to the registry there
(keep narration → WAV + duration deterministic).

**Improve parsing / figure extraction:** `core/ppv/ingest.py` (PDF/Markdown/text → text + figures);
equations come from `core/ppv/mathx.py` (arXiv LaTeX).

**Add an adapter for another agent:** mirror `adapters/claude-code/` — the adapter only needs to
read the source, author a scene plan, and shell out to the `ppv` CLI. New adapters are very welcome.

**Add tests:** there's no formal suite yet, so this is one of the most useful places to start. The
deterministic core is straightforward to cover with `pytest` — `schema.validate`/`lint` on good and
bad plans, `ingest` parsing on a sample PDF, the `ppv components`/`ppv schema` output, and a small
`--draft` render. Even a handful of cases that pin the scene-plan contract would help a lot.

## Conventions

- **Match the surrounding code** — its naming, comment density, and idioms. Python and TypeScript
  both lean terse and well-commented here.
- **Keep the CLI deterministic.** Parse/TTS/render must be reproducible from a given plan; anything
  non-deterministic belongs in the agent/adapter layer, not in `core/ppv` or the components.
- **Don't break the schema contract.** If you change component props, update both `schema.py` and
  the component, and keep `ppv validate` passing.
- **Narration is spoken, props are shown** — they're independent fields; don't conflate them.

## Submitting changes

1. Branch off `main`, keep changes focused, and make atomic commits.
2. Run `ppv validate` + a `--draft` render on an example to confirm nothing regressed.
3. Open a PR describing what changed and why, and how you verified it. Screenshots / a short clip
   help for anything visual.

For bugs and feature ideas, open an [issue](https://github.com/ssrajadh/paperview/issues) — include
`ppv doctor` output and your OS for setup problems.

## License

By contributing, you agree that your contributions are licensed under the project's
**Apache-2.0** license (see [LICENSE](LICENSE)). Note that PaperView builds on third-party tools with
their own terms (Remotion, PyMuPDF, Kokoro) — see the README's License section.
