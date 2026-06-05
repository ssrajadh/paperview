"""`ppv` CLI: the deterministic primitives the agent drives.

  ppv doctor                              health-check the toolchain
  ppv parse  <pdf|md|txt> --out <dir>     text + figures (PDF, Markdown, or text)
  ppv math   <arxiv-id|pdf> --out <dir>   real display equations from arXiv LaTeX source
  ppv validate <plan.json> [--assets D]   fast-fail plan check (no TTS/render cost)
  ppv tts    <plan.json> --out <dir>      narration WAVs + durations.json
  ppv tts    --list-voices                list TTS providers + their voices
  ppv preview <plan.json> --workdir <dir> [--scene N | --all]   single-scene still
  ppv render <plan.json> --workdir <dir> --out <mp4> [--progress]
  ppv cache  [--prune [DAYS] | --clear]   inspect / prune the parse + TTS caches
  ppv components                          per-component required/optional props
  ppv schema                              full plan JSON Schema (meta + scenes)
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

    def _default_tts():
        from .providers import DEFAULT_PROVIDER, provider_meta
        pcls = provider_meta(DEFAULT_PROVIDER)
        __import__(pcls.pip)
        return f"{pcls.pip} installed (default provider '{DEFAULT_PROVIDER}')"
    check("tts", _default_tts)
    check("soundfile", lambda: __import__("soundfile").__version__)
    check("node", lambda: subprocess.run(["node", "--version"], capture_output=True, text=True, check=True).stdout.strip())
    check("ffmpeg", lambda: subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0])
    from .render import REMOTION_DIR
    check("remotion deps", lambda: "installed" if (REMOTION_DIR / "node_modules" / "remotion").exists()
          else (_ for _ in ()).throw(RuntimeError(f"run setup; missing {REMOTION_DIR}/node_modules")))

    def _hardware():
        from .render import detect_resources, auto_concurrency
        res = detect_resources()
        c, why = auto_concurrency(res)
        gb = f"{res['available_gb']:.1f} GB free" if res["available_gb"] is not None else "RAM unknown"
        return f"{res['cores']} cores, {gb} -> render concurrency {c}"
    check("hardware", _hardware)

    print("OK" if ok else "FAILED")
    return 0 if ok else 1


def cmd_parse(args) -> int:
    from .ingest import parse_source, summarize
    manifest = parse_source(args.source, args.out, cache=not args.no_cache)
    print(summarize(manifest))
    return 0


def cmd_math(args) -> int:
    from .mathx import extract_from_source, summarize_math
    manifest = extract_from_source(args.source, args.out)
    print(summarize_math(manifest))
    return 0


def cmd_cache(args) -> int:
    from . import cache
    if args.clear:
        n, freed = cache.clear()
        print(f"cleared {n} entries ({cache.fmt_bytes(freed)} freed)")
        return 0
    if args.prune is not None:
        n, freed = cache.prune(args.prune)
        print(f"pruned {n} entries older than {args.prune:g}d ({cache.fmt_bytes(freed)} freed)")
        return 0
    print("ppv cache:")
    total = 0
    for name, (count, size) in cache.usage().items():
        total += size
        print(f"  {name:6} {count:>4} entries  {cache.fmt_bytes(size):>10}")
    print(f"  {'total':6} {'':>4}          {cache.fmt_bytes(total):>10}")
    print(f"  ({cache.ROOT})")
    return 0


def _check(plan: dict, assets_dir=None) -> int:
    """Normalize, validate (fatal), then lint (warn). Return 0 if usable, 2 if invalid."""
    schema.normalize(plan)
    errs = schema.validate(plan)
    if errs:
        print("invalid scene plan:\n  " + "\n  ".join(errs), file=sys.stderr)
        return 2
    for w in schema.lint(plan, assets_dir=assets_dir):
        print(f"  ⚠ {w}", file=sys.stderr)
    return 0


def cmd_validate(args) -> int:
    plan = _load(args.plan)
    rc = _check(plan, assets_dir=args.assets)
    if rc == 0:
        print("OK")
    return rc


def cmd_tts(args) -> int:
    from . import providers
    if args.list_voices:
        for pid in providers.provider_ids():
            pcls = providers.provider_meta(pid)
            mark = "  (default)" if pid == providers.DEFAULT_PROVIDER else ""
            print(f"{pid}{mark}: {pcls.label}")
            if pcls.voices:
                print(f"  voices (default {pcls.default_voice}): " + "  ".join(pcls.voices))
            else:
                print(f"  voices: account-specific (default {pcls.default_voice})")
        print("audition with `ppv tts <plan> --provider <id> --voice <id>`.")
        return 0
    if not args.plan or not args.out:
        print("tts: <plan> and --out are required (or use --list-voices)", file=sys.stderr)
        return 2
    plan = _load(args.plan)
    # Fold --provider/--voice into meta *before* validation, so voice is checked against the
    # effective provider (else a CLI override fails on the plan's old, now-wrong meta.voice).
    meta = plan.setdefault("meta", {})
    if args.provider is not None:
        meta["provider"] = args.provider
    if args.voice is not None:
        meta["voice"] = args.voice
    if (rc := _check(plan)) != 0:
        return rc
    from .tts import synth
    synth(plan, args.out, speed=args.speed, cache=not args.no_cache)
    return 0


def cmd_render(args) -> int:
    from .render import render
    plan = _load(args.plan)
    # the render workdir holds assets/ — check figure srcs against it too
    if (rc := _check(plan, assets_dir=str(Path(args.workdir).expanduser() / "assets"))) != 0:
        return rc
    render(plan, args.workdir, args.out, concurrency=args.concurrency, progress=args.progress,
           resolution=args.resolution, fps=args.fps, crf=args.crf, draft=args.draft,
           open_after=args.open, captions=args.captions, theme=args.theme)
    return 0


def cmd_preview(args) -> int:
    from .render import preview
    plan = _load(args.plan)
    if (rc := _check(plan, assets_dir=str(Path(args.workdir).expanduser() / "assets"))) != 0:
        return rc
    preview(plan, args.workdir, scene=args.scene, out=args.out,
            all_scenes=args.all_scenes, resolution=args.resolution, theme=args.theme)
    return 0


def cmd_components(args) -> int:
    print(schema.schema_doc())
    return 0


def cmd_schema(args) -> int:
    print(json.dumps(schema.plan_schema(), indent=2))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="ppv", description="PaperView: paper PDF -> narrated explainer video.")
    p.add_argument("--version", action="version", version=f"paperview {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="health-check the toolchain").set_defaults(func=cmd_doctor)

    sp = sub.add_parser("parse", help="extract text + figures from a PDF, Markdown, or text file")
    sp.add_argument("source"); sp.add_argument("--out", required=True)
    sp.add_argument("--no-cache", action="store_true", help="bypass the parse cache")
    sp.set_defaults(func=cmd_parse)

    sm = sub.add_parser("math", help="extract real display equations from arXiv LaTeX source")
    sm.add_argument("source", help="arXiv id / URL, or a PDF / text file that names one")
    sm.add_argument("--out", required=True)
    sm.set_defaults(func=cmd_math)

    sc = sub.add_parser("cache", help="show / prune / clear the parse + TTS caches")
    sc.add_argument("--prune", type=float, metavar="DAYS", nargs="?", const=30.0,
                    help="delete cache entries older than DAYS (default 30)")
    sc.add_argument("--clear", action="store_true", help="delete all cache entries")
    sc.set_defaults(func=cmd_cache)

    sv = sub.add_parser("validate", help="fast-fail plan check (no TTS/render cost)")
    sv.add_argument("plan")
    sv.add_argument("--assets", default=None, help="dir to check figure srcs against")
    sv.set_defaults(func=cmd_validate)

    st = sub.add_parser("tts", help="synthesize narration for a scene plan")
    st.add_argument("plan", nargs="?"); st.add_argument("--out", default=None)
    st.add_argument("--provider", default=None,
                    help="TTS engine (see --list-voices); overrides meta.provider")
    st.add_argument("--voice", default=None, help="voice id for the chosen provider")
    st.add_argument("--speed", type=float, default=1.0,
                    help="speaking-rate multiplier (1.0 = natural; >1 faster, <1 slower)")
    st.add_argument("--no-cache", action="store_true", help="bypass the per-scene narration cache")
    st.add_argument("--list-voices", action="store_true", help="list providers + voices and exit")
    st.set_defaults(func=cmd_tts)

    sr = sub.add_parser("render", help="render a scene plan to MP4")
    sr.add_argument("plan"); sr.add_argument("--workdir", required=True); sr.add_argument("--out", required=True)
    sr.add_argument("--resolution", choices=list(schema.RESOLUTIONS), default=None,
                    help=f"output size (default {schema.DEFAULT_RESOLUTION}); lower = much faster + smaller")
    sr.add_argument("--fps", type=int, default=None, help=f"frame rate (default {schema.DEFAULT_FPS})")
    sr.add_argument("--draft", action="store_true",
                    help=f"fast iteration preset ({schema.DRAFT_RESOLUTION} @ {schema.DRAFT_FPS}fps)")
    sr.add_argument("--crf", type=int, default=None,
                    help="h264 quality/size knob (higher = smaller file; Remotion default ~18)")
    sr.add_argument("--captions", action=argparse.BooleanOptionalAction, default=None,
                    help="burn per-scene narration as subtitles (--no-captions to force off)")
    sr.add_argument("--theme", choices=schema.THEMES, default=None,
                    help=f"backdrop palette (default {schema.DEFAULT_THEME}); overrides meta.theme")
    sr.add_argument("--concurrency", type=int, default=None)
    sr.add_argument("--progress", action="store_true", help="show Remotion render progress")
    sr.add_argument("--open", action="store_true", help="auto-open the MP4 when done (opt-in; default is a click-to-play link)")
    sr.set_defaults(func=cmd_render)

    pv = sub.add_parser("preview", help="render one scene (or all) to a still PNG — cheap layout check")
    pv.add_argument("plan"); pv.add_argument("--workdir", required=True)
    pv.add_argument("--scene", type=int, default=None, help="1-based scene index (default 1)")
    pv.add_argument("--all", dest="all_scenes", action="store_true", help="one still per scene")
    pv.add_argument("--out", default=None, help="output PNG (single) or directory (--all)")
    pv.add_argument("--resolution", choices=list(schema.RESOLUTIONS), default=None)
    pv.add_argument("--theme", choices=schema.THEMES, default=None)
    pv.set_defaults(func=cmd_preview)

    sub.add_parser("components", help="per-component required/optional props").set_defaults(func=cmd_components)
    sub.add_parser("schema", help="full plan JSON Schema (meta + scenes)").set_defaults(func=cmd_schema)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
