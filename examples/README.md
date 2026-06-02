# Examples

Reference scene plans authored by the agent (the `/ppv:gen` planner step), kept as
regression artifacts. Re-render any of them with the CLI:

```bash
WORK=$(mktemp -d)
~/.paperview/venv/bin/ppv parse ~/Downloads/attention_is_all_you_need.pdf --out "$WORK"
cp attention_is_all_you_need.plan.json "$WORK/plan.json"
~/.paperview/venv/bin/ppv tts    "$WORK/plan.json" --out "$WORK"
~/.paperview/venv/bin/ppv render "$WORK/plan.json" --workdir "$WORK" --out "$WORK/explainer.mp4"
```

- **attention_is_all_you_need.plan.json** — 13 scenes; uses title/statement/bullets/
  figure (Fig 1 + Fig 2 ×2)/equation (scaled dot-product + positional encoding, KaTeX)/
  comparison/stats/outro. ~2.6 min narration.
