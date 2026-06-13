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

echo "[1/6] python venv + ppv package"
[ -d "$VENV" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$REPO/core"

echo "[2/6] remotion node deps"
( cd "$REPO/core/remotion" && npm install --silent )

echo "[3/6] ffmpeg"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "  ✓ $(ffmpeg -version | head -1)"
else
  echo "  ! ffmpeg not found — install it (brew install ffmpeg  /  apt install ffmpeg)"
fi

echo "[4/6] headless-chrome system libs (Linux render dependency)"
# Remotion renders in headless Chrome, which needs a set of shared libs (libnspr4, libnss3,
# libgbm1, …). Desktop Linux and macOS already have them, but a *minimal/headless* box (a VPS,
# CI runner, or container) does NOT — and the first render dies with
# "libnspr4.so: cannot open shared object file". Install them best-effort so the box can render.
set +e
OS="$(uname -s)"
if [ "$OS" != "Linux" ]; then
  echo "  ✓ $OS — Chrome libs already present (no action)"
elif ! command -v apt-get >/dev/null 2>&1; then
  echo "  ! non-apt Linux — install Chrome's shared libs for your distro, then re-render"
  echo "    (see https://remotion.dev/docs/troubleshooting/browser-launch)"
else
  SUDO=""
  [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1 && SUDO="sudo"
  if [ "$(id -u)" -ne 0 ] && [ -z "$SUDO" ]; then
    echo "  ! need root to install Chrome libs — re-run setup as root, or manually:"
    echo "    apt-get install -y libnss3 libnspr4 libgbm1 libasound2t64 libatk-bridge2.0-0t64 \\"
    echo "      libcups2t64 libxkbcommon0 libpango-1.0-0 libxcomposite1 libxdamage1 libxrandr2 \\"
    echo "      libxfixes3 libxshmfence1 fonts-liberation"
  else
    $SUDO apt-get update -qq || true
    # Per-package so one miss doesn't abort the rest; the Ubuntu 24.04 / Debian 13 "t64"
    # transition renamed some libs, so try the new name then the pre-t64 fallback.
    fails=""
    for cand in libnss3 libnspr4 libdbus-1-3 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
                libxfixes3 libxrandr2 libgbm1 libxshmfence1 fonts-liberation libpango-1.0-0 libcairo2 \
                "libatk1.0-0t64 libatk1.0-0" "libatk-bridge2.0-0t64 libatk-bridge2.0-0" \
                "libcups2t64 libcups2" "libasound2t64 libasound2" "libatspi2.0-0t64 libatspi2.0-0"; do
      ok=0
      for pkg in $cand; do
        $SUDO apt-get install -y --no-install-recommends "$pkg" >/dev/null 2>&1 && { ok=1; break; }
      done
      [ "$ok" -eq 1 ] || fails="$fails ${cand%% *}"
    done
    [ -z "$fails" ] && echo "  ✓ chrome libs installed" \
      || echo "  ! couldn't install:$fails (render may fail; see remotion.dev browser-launch)"
  fi
fi
set -e

echo "[5/6] warm models (default TTS provider + Remotion headless Chromium)"
"$VENV/bin/python" - <<'PY'
import tempfile, os, soundfile as sf
from ppv.providers import get_provider, DEFAULT_PROVIDER
p = get_provider(DEFAULT_PROVIDER)
out = os.path.join(tempfile.mkdtemp(), "warm.wav")
p.render("Paper view setup complete.", p.default_voice, 1.0, out)
print(f"  ✓ {DEFAULT_PROVIDER} model ready (", round(sf.info(out).duration, 2), "s )")
PY
( cd "$REPO/core/remotion" && npx remotion browser ensure >/dev/null 2>&1 && echo "  ✓ chromium shell ready" || echo "  ! chromium ensure failed (will download on first render)" )

echo "[6/6] doctor"
"$VENV/bin/ppv" doctor

echo
echo "✅ setup complete.  ppv -> $VENV/bin/ppv"
