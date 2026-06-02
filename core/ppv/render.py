"""Render a scene plan to MP4 via the bundled Remotion project.

Stages the run's assets/audio + plan/durations into the Remotion project, then
runs `npx remotion render`. The project is found relative to this package source
(editable install), so node_modules live in core/remotion (installed by setup).
"""
from __future__ import annotations
import json
import shutil
import subprocess
import time
from pathlib import Path

REMOTION_DIR = Path(__file__).resolve().parents[1] / "remotion"


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
           progress: bool = False) -> dict:
    work = Path(workdir)
    out_mp4 = str(Path(out_mp4).expanduser().resolve())
    public = REMOTION_DIR / "public"

    n_assets = _clear_and_copy(work / "assets", public / "assets")
    n_audio = _clear_and_copy(work / "audio", public / "audio")

    # fold measured narration durations into the plan, then pass it as input props
    # (nothing in the repo's src/ is touched — per-run data stays in the workdir)
    durmap = {d["id"]: d["duration"] for d in json.loads((work / "durations.json").read_text())}
    scenes = [{**s, "seconds": durmap.get(s["id"], 3)} for s in plan["scenes"]]
    merged = {**plan, "meta": {**plan.get("meta", {}), "audio": True}, "scenes": scenes}
    props_file = work / "_props.json"
    props_file.write_text(json.dumps({"plan": merged}))

    # default to quiet (just the summary line below); --progress lets Remotion's
    # progress bar through, useful for a long backgrounded render (~minutes of silence)
    cmd = ["npx", "remotion", "render", "src/index.ts", "Paper", out_mp4,
           f"--props={props_file}"]
    if not progress:
        cmd.append("--log=error")
    if concurrency:
        cmd.append(f"--concurrency={concurrency}")

    print(f"  staged {n_assets} assets, {n_audio} audio clips; rendering -> {out_mp4}")
    t0 = time.time()
    subprocess.run(cmd, cwd=REMOTION_DIR, check=True)
    wall = time.time() - t0

    size = Path(out_mp4).stat().st_size
    print(f"  rendered in {wall:.1f}s  ({size/1e6:.1f} MB)  -> {out_mp4}")
    return {"out": out_mp4, "seconds": round(wall, 1), "bytes": size}
