"""Inspect and prune the on-disk caches (D7). Two caches live under ~/.paperview/cache:
`parse/<key>/` (per-source extracted text + figures) and `tts/<key>.wav` (per-scene
narration). Entries are content-addressed, so pruning by age is always safe — a pruned
entry is just re-created on next use."""
from __future__ import annotations
import shutil
import time
from pathlib import Path

ROOT = Path.home() / ".paperview" / "cache"
CACHES = {"parse": ROOT / "parse", "tts": ROOT / "tts"}


def _entries(d: Path) -> list[Path]:
    """Top-level cache entries in `d` (a parse dir or a tts wav)."""
    return [p for p in d.iterdir()] if d.is_dir() else []


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def fmt_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def usage() -> dict[str, tuple[int, int]]:
    """name -> (entry count, total bytes) for each cache."""
    return {name: (len(_entries(d)), _size(d) if d.exists() else 0) for name, d in CACHES.items()}


def prune(days: float) -> tuple[int, int]:
    """Delete entries not modified in the last `days`. Returns (entries removed, bytes freed)."""
    cutoff = time.time() - days * 86400
    removed, freed = 0, 0
    for d in CACHES.values():
        for entry in _entries(d):
            if entry.stat().st_mtime < cutoff:
                freed += _size(entry)
                removed += 1
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    return removed, freed


def clear() -> tuple[int, int]:
    """Delete every cache entry. Returns (entries removed, bytes freed)."""
    removed, freed = 0, 0
    for d in CACHES.values():
        for entry in _entries(d):
            freed += _size(entry)
            removed += 1
            shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
    return removed, freed
