"""`ppv` CLI: the deterministic primitives the agent drives.

  ppv doctor                              health-check the toolchain
  ppv parse  <pdf>  --out <dir>           text per page + extracted figures
  ppv tts    <plan.json> --out <dir>      narration WAVs + durations.json
  ppv render <plan.json> --workdir <dir> --out <mp4>
  ppv components                          print the scene-plan component reference
"""
from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from . import schema


def _load(path: str) -> dict:
    return json.loads(Path(path).expanduser().read_text())


def cmd_doctor(args) -> int:
    ok = True

    def check(label, fn):
        nonlocal ok
        try:
            detail = fn()
            print(f"  ✓ {label}: {detail}")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  ✗ {label}: {e}")

    print("ppv doctor")
    check("pymupdf", lambda: __import__("fitz").VersionBind)
    check("supertonic", lambda: __import__("supertonic").__version__ if hasattr(__import__("supertonic"), "__version__") else "installed")
    check("soundfile", lambda: __import__("soundfile").__version__)
    check("node", lambda: subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip())
    check("ffmpeg", lambda: subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0])
    from .render import REMOTION_DIR
    check("remotion deps", lambda: "installed" if (REMOTION_DIR / "node_modules" / "remotion").exists()
          else (_ for _ in ()).throw(RuntimeError(f"run setup; missing {REMOTION_DIR}/node_modules")))
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


def cmd_parse(args) -> int:
    from .ingest import parse, summarize
    manifest = parse(args.pdf, args.out)
    print(summarize(manifest))
    return 0


def cmd_tts(args) -> int:
    from .tts import synth
    plan = _load(args.plan)
    errs = schema.validate(plan)
    if errs:
        print("invalid scene plan:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 2
    synth(plan, args.out, voice=args.voice)
    return 0


def cmd_render(args) -> int:
    from .render import render
    plan = _load(args.plan)
    errs = schema.validate(plan)
    if errs:
        print("invalid scene plan:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 2
    render(plan, args.workdir, args.out, concurrency=args.concurrency)
    return 0


def cmd_components(args) -> int:
    print(schema.schema_doc())
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ppv", description="PaperView: paper PDF -> narrated explainer video.")
    p.add_argument("--version", action="version", version=f"paperview {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="health-check the toolchain").set_defaults(func=cmd_doctor)

    sp = sub.add_parser("parse", help="extract text + figures from a PDF")
    sp.add_argument("pdf"); sp.add_argument("--out", required=True)
    sp.set_defaults(func=cmd_parse)

    st = sub.add_parser("tts", help="synthesize narration for a scene plan")
    st.add_argument("plan"); st.add_argument("--out", required=True); st.add_argument("--voice", default=None)
    st.set_defaults(func=cmd_tts)

    sr = sub.add_parser("render", help="render a scene plan to MP4")
    sr.add_argument("plan"); sr.add_argument("--workdir", required=True); sr.add_argument("--out", required=True)
    sr.add_argument("--concurrency", type=int, default=None)
    sr.set_defaults(func=cmd_render)

    sub.add_parser("components", help="print the scene-plan component reference").set_defaults(func=cmd_components)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
