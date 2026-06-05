---
description: One-time toolchain bootstrap for PaperView (Python venv, Remotion deps, local models). Run once before /ppv:gen.
disable-model-invocation: true
---

# /ppv:setup — bootstrap the PaperView toolchain

Provision everything `/ppv:gen` needs to run locally. This is idempotent — safe to re-run.

## Steps

1. **Locate the paperview repo** (the directory containing `core/` and `scripts/setup.sh`).
   Try, in order: the current working directory, then `git rev-parse --show-toplevel`, then
   search nearby (`find . ~ -maxdepth 4 -name setup.sh -path '*paperview/scripts*' 2>/dev/null`).
   If you cannot find it, ask the user where they cloned `paperview`.

2. **Run the setup script** and stream its output:
   ```bash
   bash <repo>/scripts/setup.sh
   ```
   It creates `~/.paperview/venv` with the `ppv` CLI, installs the Remotion node deps, checks
   ffmpeg, and warms the Kokoro TTS + Chromium models (first run downloads them — may take a few
   minutes).

3. **Confirm health** by running the doctor and showing its output:
   ```bash
   ~/.paperview/venv/bin/ppv doctor
   ```

4. Report success and tell the user they can now run `/ppv:gen <pdf path and any options>`.
   If ffmpeg was missing, tell them to install it and re-run setup.
