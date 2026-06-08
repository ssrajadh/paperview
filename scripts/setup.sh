#!/usr/bin/env bash
# One-time toolchain bootstrap for PaperView. Idempotent.
# Installs the `ppv` CLI into ~/.paperview/venv, the Remotion deps, and warms models.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PPV_HOME="${PPV_HOME:-$HOME/.paperview}"
VENV="$PPV_HOME/venv"

echo "paperview setup"
echo "  repo: $REPO"
echo "  home: $PPV_HOME"
mkdir -p "$PPV_HOME"

echo "[1/5] python venv + ppv package"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$REPO/core"

echo "[2/5] remotion node deps"
( cd "$REPO/core/remotion" && npm install --silent )

echo "[3/5] ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "  ✓ $(ffmpeg -version | head -1)"
else
  echo "  ! ffmpeg not found — install it (brew install ffmpeg  /  apt install ffmpeg)"
fi

echo "[4/5] warm models (default TTS provider + Remotion headless Chromium)"
"$VENV/bin/python" - <<'PY'
import tempfile, os, soundfile as sf
from ppv.providers import get_provider, DEFAULT_PROVIDER
p = get_provider(DEFAULT_PROVIDER)
out = os.path.join(tempfile.mkdtemp(), "warm.wav")
p.render("Paper view setup complete.", p.default_voice, 1.0, out)
print(f"  ✓ {DEFAULT_PROVIDER} model ready (", round(sf.info(out).duration, 2), "s )")
PY
( cd "$REPO/core/remotion" && npx remotion browser ensure >/dev/null 2>&1 && echo "  ✓ chromium shell ready" || echo "  ! chromium ensure failed (will download on first render)" )

echo "[5/5] doctor"
"$VENV/bin/ppv" doctor

echo
echo "✅ setup complete.  ppv -> $VENV/bin/ppv"
