#!/usr/bin/env bash
# One-time toolchain bootstrap for PaperView. Idempotent and re-runnable: every step guards on the
# thing it produces (and rebuilds it if a previous run left it half-done), so "just re-run setup"
# actually recovers. Installs the `ppv` CLI into ~/.paperview/venv, the Remotion deps, and warms models.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PPV_HOME="${PPV_HOME:-$HOME/.paperview}"
VENV="$PPV_HOME/venv"
OS_NAME="$(uname -s)"

# Best-effort apt installer for Debian/Ubuntu. `APT` is set only when we can actually install
# (root, or non-root with sudo), so callers branch on it for a clear message otherwise. The same
# helper backs every system dependency we pull (python venv, ffmpeg, Chrome libs) — one place, one
# behavior, rather than auto-installing some deps and leaving others as manual chores.
APT=""
if [ "$OS_NAME" = "Linux" ] && command -v apt-get >/dev/null 2>&1; then
  if [ "$(id -u)" -eq 0 ]; then APT="apt-get"
  elif command -v sudo >/dev/null 2>&1; then APT="sudo apt-get"; fi
fi
_apt_updated=""
apt_install() {  # apt_install <pkg>...  -> 0 if installed; 1 if we can't apt at all
  [ -n "$APT" ] || return 1
  [ -n "$_apt_updated" ] || { $APT update -qq || true; _apt_updated=1; }
  $APT install -y --no-install-recommends "$@" >/dev/null 2>&1
}

echo "paperview setup"
echo "  repo: $REPO"
echo "  home: $PPV_HOME"
mkdir -p "$PPV_HOME"

echo "[0/6] prerequisites"
# Tools setup itself needs: git, python3 (for the venv), node/npm (for Remotion). Auto-install on
# Linux/apt; otherwise (macOS, or no root) halt with one clear remediation line instead of a
# confusing traceback three steps in — a fresh Mac with no Node was a launch blocker.
need=""
command -v git     >/dev/null 2>&1 || need="$need git"
command -v python3 >/dev/null 2>&1 || need="$need python3"
command -v node    >/dev/null 2>&1 || need="$need nodejs"
command -v npm     >/dev/null 2>&1 || need="$need npm"
if [ -n "$need" ]; then
  echo "  missing:$need — attempting install…"
  apt_install $need || true
fi
miss=""
for c in git python3 node npm; do command -v "$c" >/dev/null 2>&1 || miss="$miss $c"; done
if [ -n "$miss" ]; then
  echo "  ✗ required tools still missing:$miss — install them, then re-run setup:"
  echo "      macOS:          brew install git python node     (or get Node from https://nodejs.org)"
  echo "      Debian/Ubuntu:  sudo apt-get install -y git python3 python3-venv nodejs npm"
  exit 1
fi
echo "  ✓ git, python3, node, npm present"

echo "[1/6] python venv + ppv package"
# Guard on the venv's pip, not just the directory: a half-created venv from a failed earlier run
# leaves the dir behind but no bin/pip, so a dir-only guard ([ -d ]) would skip the rebuild and then
# die on a missing pip — the bug that made "re-run setup" unrecoverable. Rebuild with --clear.
if [ ! -x "$VENV/bin/pip" ]; then
  if ! python3 -m venv --clear "$VENV" 2>/dev/null; then
    # fresh Debian/Ubuntu often ships python3 without venv/ensurepip — install it, then retry.
    echo "  python venv support missing; installing python3-venv…"
    pyv="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
    apt_install python3-venv "python${pyv}-venv" python3-pip || true
    python3 -m venv --clear "$VENV" || {
      echo "  ✗ could not create a Python venv. Install venv support, then re-run setup:"
      echo "      sudo apt-get install -y python3-venv     # Debian/Ubuntu"
      echo "      (macOS: python3 from python.org or Homebrew already includes venv)"
      exit 1
    }
  fi
fi
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$REPO/core"

echo "[2/6] remotion node deps"
( cd "$REPO/core/remotion" && npm install --silent )

echo "[3/6] ffmpeg"
# A hard render dependency — auto-install it on Linux just like the Chrome libs below, so the box
# isn't left half-provisioned (and `ppv doctor` at the end doesn't fail on a missing ffmpeg after
# minutes of warm-up).
command -v ffmpeg >/dev/null 2>&1 || apt_install ffmpeg || true
if command -v ffmpeg >/dev/null 2>&1; then
  echo "  ✓ $(ffmpeg -version | head -1)"
else
  echo "  ! ffmpeg not found and couldn't auto-install — install it, then re-run setup:"
  echo "      brew install ffmpeg              # macOS"
  echo "      sudo apt-get install -y ffmpeg   # Debian/Ubuntu"
fi

echo "[4/6] headless-chrome system libs (Linux render dependency)"
# Remotion renders in headless Chrome, which needs shared libs (libnspr4, libnss3, libgbm1, …).
# Desktop Linux and macOS already have them, but a minimal/headless box (a VPS, CI runner, or
# container) does NOT — and the first render dies with "libnspr4.so: cannot open shared object file".
set +e
if [ "$OS_NAME" != "Linux" ]; then
  echo "  ✓ ${OS_NAME} — Chrome libs already present (no action)"
elif [ -z "$APT" ]; then
  if ! command -v apt-get >/dev/null 2>&1; then
    echo "  ! non-apt Linux — install Chrome's shared libs for your distro"
    echo "    (see https://remotion.dev/docs/troubleshooting/browser-launch)"
  else
    echo "  ! need root to install Chrome libs — re-run setup as root/sudo, or manually:"
    echo "      apt-get install -y libnss3 libnspr4 libgbm1 libasound2t64 libatk-bridge2.0-0t64 \\"
    echo "        libcups2t64 libxkbcommon0 libpango-1.0-0 libxcomposite1 libxdamage1 libxrandr2 \\"
    echo "        libxfixes3 libxshmfence1 fonts-liberation"
  fi
else
  # Per-package so one miss doesn't abort the rest; the Ubuntu 24.04 / Debian 13 "t64" transition
  # renamed some libs, so try the new name then the pre-t64 fallback.
  fails=""
  for cand in libnss3 libnspr4 libdbus-1-3 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
              libxfixes3 libxrandr2 libgbm1 libxshmfence1 fonts-liberation libpango-1.0-0 libcairo2 \
              "libatk1.0-0t64 libatk1.0-0" "libatk-bridge2.0-0t64 libatk-bridge2.0-0" \
              "libcups2t64 libcups2" "libasound2t64 libasound2" "libatspi2.0-0t64 libatspi2.0-0"; do
    ok=0
    for pkg in $cand; do apt_install "$pkg" && { ok=1; break; }; done
    [ "$ok" -eq 1 ] || fails="$fails ${cand%% *}"
  done
  [ -z "$fails" ] && echo "  ✓ chrome libs installed" \
    || echo "  ! couldn't install:$fails (render may fail; see remotion.dev browser-launch)"
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
