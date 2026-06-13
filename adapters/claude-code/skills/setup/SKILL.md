---
description: One-time toolchain bootstrap for PaperView (Python venv, Remotion deps, local models). Run once before /ppv:gen.
disable-model-invocation: true
---

# /ppv:setup — bootstrap the PaperView toolchain

Provision everything `/ppv:gen` needs to run locally. This is idempotent — safe to re-run.

## Steps

1. **Locate the repo root + run the setup script** — one block, so `$REPO` is in scope.
   Installed from the marketplace, this skill runs with `$CLAUDE_PLUGIN_ROOT` set to the plugin dir
   (`adapters/claude-code`), so the repo root (which holds `core/` and `scripts/setup.sh`) is two
   levels up — no separate `git clone` required. Resolve it robustly, then run the script and stream
   its output:
   ```bash
   REPO="$(cd "${CLAUDE_PLUGIN_ROOT:-.}/../.." 2>/dev/null && pwd)"
   [ -f "$REPO/scripts/setup.sh" ] || REPO="$(git rev-parse --show-toplevel 2>/dev/null)"
   [ -f "$REPO/scripts/setup.sh" ] || REPO="$(find ~ . -maxdepth 6 -name setup.sh -path '*paperview/scripts*' 2>/dev/null | head -1 | xargs -r dirname | xargs -r dirname)"
   [ -f "$REPO/scripts/setup.sh" ] || { echo "couldn't find paperview repo — ask the user where it lives"; exit 1; }
   echo "repo: $REPO"
   bash "$REPO/scripts/setup.sh"
   ```
   If the resolver prints the error and exits, ask the user where they cloned/installed `paperview`,
   then run `bash <that path>/scripts/setup.sh`. The script creates `~/.paperview/venv` with the `ppv`
   CLI, installs the Remotion node deps, checks ffmpeg, and warms the Kokoro TTS + Chromium models
   (first run downloads them — may take a few minutes).

2. **Confirm health** by running the doctor and showing its output:
   ```bash
   ~/.paperview/venv/bin/ppv doctor
   ```

3. Report success and tell the user they can now run `/ppv:gen <pdf path and any options>`.
   If ffmpeg was missing, tell them to install it and re-run setup.
