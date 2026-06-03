"""Render a scene plan to MP4 via the bundled Remotion project.

Stages the run's assets/audio + plan/durations into the Remotion project, then
runs `npx remotion render`. The project is found relative to this package source
(editable install), so node_modules live in core/remotion (installed by setup).
"""
from __future__ import annotations
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

TRANSITION = 12  # must match remotion/src/layout.ts

REMOTION_DIR = Path(__file__).resolve().parents[1] / "remotion"

# Rough peak RAM per parallel headless-Chrome render worker. Remotion's own default
# concurrency (~cores/2) is RAM-blind, so on a many-core / low-RAM box it thrashes or
# gets OOM-killed; we cap by available memory too. Tune if renders still thrash.
MEM_PER_WORKER_GB = 1.5


def _available_gb() -> float | None:
    """Best-effort available RAM in GB (None if undetectable). Linux MemAvailable first."""
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024 * 1024)  # kB -> GB
    except Exception:  # noqa: BLE001
        pass
    try:
        return (os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES")) / (1024 ** 3)
    except (ValueError, OSError, AttributeError):
        return None


def detect_resources() -> dict:
    return {"cores": os.cpu_count() or 1, "available_gb": _available_gb()}


def auto_concurrency(res: dict | None = None, mem_scale: float = 1.0) -> tuple[int, str]:
    """Pick a render concurrency that adapts to the machine: bounded by cores AND by
    available RAM. `mem_scale` is the per-worker RAM multiplier for the output resolution
    (lower res -> lighter workers -> more of them fit). Returns (concurrency, reason).
    Output is unaffected — this only changes how fast/safely it renders."""
    res = res or detect_resources()
    cores = res["cores"]
    gb = res["available_gb"]
    per_worker = MEM_PER_WORKER_GB * mem_scale
    by_cores = max(1, cores - 1)  # leave a core for the system
    if gb is None:
        return by_cores, f"{cores} cores, RAM unknown -> {by_cores}"
    by_mem = max(1, int(gb // per_worker))
    c = max(1, min(by_cores, by_mem))
    return c, (f"{cores} cores, {gb:.1f} GB free -> "
               f"min(cores-1={by_cores}, mem/{per_worker:.2g}GB={by_mem}) = {c}")


def _link(path: str, label: str | None = None) -> str:
    """Render an absolute path as an OSC 8 terminal hyperlink (file://). Clicking it in a
    supporting terminal (GNOME Terminal, iTerm2, kitty, VS Code…) opens it with the OS
    default handler — i.e. plays the video — with no intrusive auto-open. Plain path is
    still shown for terminals that ignore the escape."""
    from urllib.request import pathname2url
    uri = "file://" + pathname2url(str(path))
    return f"\033]8;;{uri}\033\\{label or path}\033]8;;\033\\"


def _open_file(path: str) -> bool:
    """Opt-in (`--open`) best-effort OS opener; non-blocking, never raises."""
    import sys
    try:
        cmd = (["open", path] if sys.platform == "darwin"
               else ["cmd", "/c", "start", "", path] if sys.platform.startswith("win")
               else ["xdg-open", path])
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:  # noqa: BLE001
        return False


def _clear_and_copy(src: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    for p in dst.iterdir():
        if p.is_file():
            p.unlink()
    n = 0
    if src.is_dir():
        for p in src.iterdir():
            if p.is_file():
                shutil.copy2(p, dst / p.name)
                n += 1
    return n


def render(plan: dict, workdir: str, out_mp4: str, concurrency: int | None = None,
           progress: bool = False, resolution: str | None = None, fps: int | None = None,
           crf: int | None = None, draft: bool = False, open_after: bool = False) -> dict:
    from . import schema
    work = Path(workdir)
    out_mp4 = str(Path(out_mp4).expanduser().resolve())
    public = REMOTION_DIR / "public"
    meta = plan.get("meta", {})

    # resolve output knobs (intent-driven, never hardware): explicit arg > --draft >
    # meta > default. resolution -> Remotion --scale (composition stays 1080-logical, so
    # component layout is unchanged); fps flows into the props so timing matches.
    if draft:
        resolution = resolution or schema.DRAFT_RESOLUTION
        fps = fps or schema.DRAFT_FPS
    resolution = resolution or meta.get("resolution") or schema.DEFAULT_RESOLUTION
    fps = fps or meta.get("fps") or schema.DEFAULT_FPS
    scale = schema.RESOLUTIONS[resolution]
    bw, bh = schema.ASPECTS.get(meta.get("aspect", "16:9"), (1920, 1080))
    out_w, out_h = round(bw * scale), round(bh * scale)

    n_assets = _clear_and_copy(work / "assets", public / "assets")
    n_audio = _clear_and_copy(work / "audio", public / "audio")

    # fold measured narration durations into the plan, then pass it as input props
    # (nothing in the repo's src/ is touched — per-run data stays in the workdir)
    durmap = {d["id"]: d["duration"] for d in json.loads((work / "durations.json").read_text())}
    scenes = [{**s, "seconds": durmap.get(s["id"], 3)} for s in plan["scenes"]]
    merged = {**plan, "meta": {**meta, "audio": True, "fps": fps, "resolution": resolution},
              "scenes": scenes}
    props_file = work / "_props.json"
    props_file.write_text(json.dumps({"plan": merged}))

    # default to quiet (just the summary line below); --progress lets Remotion's
    # progress bar through, useful for a long backgrounded render (~minutes of silence)
    cmd = ["npx", "remotion", "render", "src/index.ts", "Paper", out_mp4,
           f"--props={props_file}"]
    if not progress:
        cmd.append("--log=error")
    if scale != 1.0:
        cmd.append(f"--scale={scale}")
    if crf is not None:
        cmd.append(f"--crf={crf}")
    if concurrency is None:
        concurrency, why = auto_concurrency(mem_scale=scale * scale)
        print(f"  auto-concurrency {concurrency} ({why})")
    cmd.append(f"--concurrency={concurrency}")

    crf_note = f", crf {crf}" if crf is not None else ""
    print(f"  {resolution} {out_w}x{out_h} @ {fps}fps{crf_note}")
    print(f"  staged {n_assets} assets, {n_audio} audio clips; rendering -> {out_mp4}")
    t0 = time.time()
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True)
    wall = time.time() - t0

    size = Path(out_mp4).stat().st_size
    print(f"  rendered in {wall:.1f}s  ({size/1e6:.1f} MB)")
    print(f"  ▶ {_link(out_mp4)}   (click to play)")
    if open_after and _open_file(out_mp4):
        print("  opening in your default player…")
    return {"out": out_mp4, "seconds": round(wall, 1), "bytes": size,
            "resolution": resolution, "fps": fps}


def _scene_frames(seconds: float, fps: int) -> int:
    return max(1, math.ceil((seconds if seconds is not None else 3) * fps))


def _content_end_frame(scenes: list[dict], idx: int, fps: int) -> int:
    """Frame where scene `idx` is fully revealed and shown alone. On the transitioned
    timeline the tail overlap cancels exactly, so each scene starts at the cumulative
    sceneFrames; we capture its last content frame (before the fade tail)."""
    start = sum(_scene_frames(s.get("seconds"), fps) for s in scenes[:idx])
    return start + _scene_frames(scenes[idx].get("seconds"), fps) - 1


def preview(plan: dict, workdir: str, scene: int | None = None, out: str | None = None,
            all_scenes: bool = False, resolution: str | None = None) -> list[str]:
    """Render a single scene (or every scene) to a still PNG — a cheap layout check
    before committing to a multi-minute video render. No TTS/audio needed."""
    from . import schema
    work = Path(workdir)
    public = REMOTION_DIR / "public"
    meta = plan.get("meta", {})
    resolution = resolution or meta.get("resolution") or schema.DEFAULT_RESOLUTION
    fps = meta.get("fps") or schema.DEFAULT_FPS
    scale = schema.RESOLUTIONS[resolution]

    _clear_and_copy(work / "assets", public / "assets")  # figures must be staged

    # use measured durations if a `ppv tts` run exists, else a default so reveals settle
    durfile = work / "durations.json"
    durmap = {d["id"]: d["duration"] for d in json.loads(durfile.read_text())} if durfile.exists() else {}
    scenes = [{**s, "seconds": durmap.get(s["id"], 5)} for s in plan["scenes"]]
    merged = {**plan, "meta": {**meta, "audio": False, "fps": fps, "resolution": resolution},
              "scenes": scenes}
    props_file = work / "_preview_props.json"
    props_file.write_text(json.dumps({"plan": merged}))

    n = len(scenes)
    if all_scenes:
        out_dir = Path(out).expanduser() if out else (work / "preview")
        out_dir.mkdir(parents=True, exist_ok=True)
        targets = [(i, out_dir / f"scene{scenes[i]['id']}.png") for i in range(n)]
    else:
        idx = (scene or 1) - 1
        if not (0 <= idx < n):
            raise SystemExit(f"--scene {scene} out of range (1..{n})")
        targets = [(idx, Path(out).expanduser() if out else work / f"preview_scene{scenes[idx]['id']}.png")]

    results = []
    for idx, opng in targets:
        frame = _content_end_frame(scenes, idx, fps)
        opng.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["npx", "remotion", "still", "src/index.ts", "Paper", str(opng),
               f"--props={props_file}", f"--frame={frame}", "--log=error"]
        if scale != 1.0:
            cmd.append(f"--scale={scale}")
        subprocess.run(cmd, cwd=REMOTION_DIR, check=True)
        sid = scenes[idx]["id"]
        comp = scenes[idx].get("component", "?")
        print(f"  scene {sid:>2} ({comp}, frame {frame}) -> {opng}")
        results.append(str(opng))
    return results
