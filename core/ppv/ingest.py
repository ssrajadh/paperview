"""Source ingest -> parse.json (per-"page" text + figures in assets/). PDF figures are
captured by clip-rendering the region around each "Figure/Table N" caption, which grabs
**vector** figures the embedded-image API misses (D2), and records the caption text too;
falls back to embedded raster on pages with no detected captions. Markdown/text/HTML are
read directly (no PDF round-trip). All sources emit the same manifest shape so the planner
is source-agnostic."""
from __future__ import annotations
import hashlib
import json
import re
import shutil
from pathlib import Path

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text", ".rst", ".html", ".htm", ".tex"}

# Parse cache (D7): re-parsing the same source is wasted work, so cache parse.json + the
# extracted assets by source content. Bump INGEST_VERSION when extraction logic changes so
# stale results are invalidated automatically.
INGEST_VERSION = "2"
CACHE_DIR = Path.home() / ".paperview" / "cache" / "parse"


def _source_key(src: Path) -> str:
    """Content-addressed key for a source file (ingest version + suffix + bytes)."""
    h = hashlib.sha256(f"{INGEST_VERSION}|{src.suffix.lower()}|".encode())
    with open(src, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:20]


def _restore_parse(cdir: Path, out: Path) -> dict:
    """Copy a cached parse (parse.json + assets/) into `out`, fixing the assets path."""
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    for p in (cdir / "assets").glob("*"):
        if p.is_file():
            shutil.copy2(p, assets / p.name)
    manifest = json.loads((cdir / "parse.json").read_text())
    manifest["assets_dir"] = str(assets)
    (out / "parse.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def _store_parse(out: Path, cdir: Path) -> None:
    """Save a fresh parse (parse.json + assets/) into the cache dir."""
    cassets = cdir / "assets"
    cassets.mkdir(parents=True, exist_ok=True)
    for p in (out / "assets").glob("*"):
        if p.is_file():
            shutil.copy2(p, cassets / p.name)
    shutil.copy2(out / "parse.json", cdir / "parse.json")

# A caption block: "Figure 3:", "Fig. 3.", "Table 3 —". The trailing separator avoids
# matching in-body reference sentences like "Table 2 summarizes our results".
_CAP_RE = re.compile(r"^\s*(figure|fig\.?|table)\s+([0-9]+)\s*[:.–—]", re.IGNORECASE)


def parse_source(src: str, out_dir: str, cache: bool = True) -> dict:
    """Dispatch on file type: PDF -> PyMuPDF; markdown/text/HTML -> read directly. Results
    are content-addressed cached (D7) — re-parsing an unchanged source restores the cached
    parse.json + assets instead of re-extracting. Bypass with cache=False."""
    p = Path(src).expanduser()
    out = Path(out_dir)
    key = _source_key(p) if cache and p.is_file() else None
    if key is not None and (CACHE_DIR / key / "parse.json").exists():
        print("  [cache] parse hit — restoring extracted text + figures")
        return _restore_parse(CACHE_DIR / key, out)

    manifest = parse(src, out_dir) if p.suffix.lower() == ".pdf" else parse_text(src, out_dir)
    if key is not None:
        try:
            _store_parse(out, CACHE_DIR / key)
        except OSError:
            pass  # caching is best-effort; never fail a parse over it
    return manifest


def _cluster_rects(rects: list[list[float]], gap: float = 18.0) -> list[list[float]]:
    """Merge rects whose bboxes are within `gap` into connected components. Drawn strokes +
    embedded images of one figure cluster into its region; this is robust to text *inside*
    the figure (axis labels, table cells) because we cluster the drawn content, not bound by
    surrounding text."""
    rects = [list(r) for r in rects]
    changed = True
    while changed:
        changed = False
        out: list[list[float]] = []
        for r in rects:
            for o in out:
                if not (r[0] > o[2] + gap or r[2] < o[0] - gap or r[1] > o[3] + gap or r[3] < o[1] - gap):
                    o[0], o[1] = min(o[0], r[0]), min(o[1], r[1])
                    o[2], o[3] = max(o[2], r[2]), max(o[3], r[3])
                    changed = True
                    break
            else:
                out.append(r)
        rects = out
    return rects


def _table_region_from_text(blocks: list, cap, pr, max_gap: float = 26.0) -> list[float] | None:
    """Reconstruct a table's bbox from the text rows below its caption, for borderless /
    low-rule tables that leave little drawn content to cluster. Grows downward from the
    caption through tightly-spaced rows, stopping at a large vertical gap or the next
    caption. Returns [x0,y0,x1,y1] or None if nothing tabular sits below the caption."""
    cy_mid = (cap[1] + cap[3]) / 2
    below = sorted((b for b in blocks if (b[1] + b[3]) / 2 > cy_mid and b is not cap),
                   key=lambda b: b[1])
    region: list[float] | None = None
    prev_bottom = cap[3]
    for b in below:
        x0, y0, x1, y1 = b[:4]
        if _CAP_RE.match(b[4]):  # next figure/table caption -> table has ended
            break
        # table rows are single-line cells; a tall, wordy block is body prose, which in a
        # two-column layout flows right under the table — stop before absorbing it.
        prose = (y1 - y0) > 48 or len(b[4].split()) > 28
        if region is not None:
            if y0 - prev_bottom > max_gap or prose:  # big gap or prose -> table has ended
                break
            if x0 > region[2] + 40 or x1 < region[0] - 40:  # a side column of prose, not a row
                continue
            region = [min(region[0], x0), min(region[1], y0),
                      max(region[2], x1), max(region[3], y1)]
        else:
            if y0 - cap[3] > max_gap * 2:  # first block far below the caption -> no table here
                break
            # accept the first adjacent block as the table body even if tall/wordy — PyMuPDF
            # often returns a whole table as one block; the prose stop above bounds the rest.
            region = [x0, y0, x1, y1]
        prev_bottom = y1
        if region[3] - region[1] > pr.height * 0.6:  # runaway -> stop growing
            break
    return region


def _clip_figures(page, page_no: int, assets: Path, min_fig_px: int, zoom: float = 2.0) -> list[dict]:
    """Caption-anchored clip-render. Cluster the page's drawn content + images into figure
    regions, assign each figure/table caption to the nearest region on the expected side
    (above for figures, below for tables), and rasterize it — capturing vector figures (and
    tables, via their rule lines) that the embedded-image API misses."""
    import fitz

    pr = page.rect
    blocks = [b for b in page.get_text("blocks") if b[6] == 0 and b[4].strip()]
    content = [list(d["rect"]) for d in page.get_drawings()]
    for img in page.get_images(full=True):
        try:
            content += [[r.x0, r.y0, r.x1, r.y1] for r in page.get_image_rects(img[0])]
        except Exception:  # noqa: BLE001
            pass
    content = [r for r in content if r[2] - r[0] > 1 and r[3] - r[1] > 1]
    if len(content) > 4000:  # pathological page (vector soup) -> let the fallback handle it
        return []

    min_pt = min_fig_px / zoom
    # an empty cluster list is fine: a borderless table leaves no drawn content but its
    # region can still be reconstructed from the text rows below the caption (below).
    clusters = [c for c in _cluster_rects(content)
                if c[2] - c[0] >= min_pt and c[3] - c[1] >= min_pt]

    figures = []
    for b in blocks:
        m = _CAP_RE.match(b[4])
        if not m:
            continue
        kind = "table" if m.group(1).lower() == "table" else "figure"
        label = f"{'Table' if kind == 'table' else 'Figure'} {m.group(2)}"
        cx0, cy0, cx1, cy1 = b[:4]
        ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2

        def vgap(c) -> float:  # 0 if the caption is within the region's y-span
            return max(0.0, c[1] - ccy, ccy - c[3])

        cands = [c for c in clusters if not (c[2] < cx0 - 5 or c[0] > cx1 + 5) or c[0] <= ccx <= c[2]]
        # a figure sits above its caption, a table below — judged by region *center* so the
        # caption may overlap the figure's bottom edge (common when content runs to the caption)
        side = [c for c in cands if ((c[1] + c[3]) / 2 <= ccy) == (kind == "figure")]
        grp = side or cands
        pick = min(grp, key=vgap) if grp else None
        # tables: if no drawn cluster fits (borderless), reconstruct the region from text rows
        if kind == "table" and (pick is None or vgap(pick) > pr.height * 0.25):
            tr = _table_region_from_text(blocks, b, pr)
            if tr is not None:
                pick = tr
        if pick is None or vgap(pick) > pr.height * 0.4:  # nothing plausible -> skip
            continue
        # clip to the region but trim out the caption text itself (below for figs, above for tables)
        x0, y0, x1, y1 = pick[0] - 4, pick[1] - 4, pick[2] + 4, pick[3] + 4
        y1 = min(y1, cy0 - 2) if kind == "figure" else y1
        y0 = max(y0, cy1 + 2) if kind == "table" else y0
        clip = fitz.Rect(max(pr.x0, x0), max(pr.y0, y0), min(pr.x1, x1), min(pr.y1, y1))
        if clip.width * zoom < min_fig_px or clip.height * zoom < min_fig_px:
            continue
        pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        fname = f"fig_p{page_no}_{kind}{m.group(2)}.png"
        pm.save(str(assets / fname))
        figures.append({"file": fname, "page": page_no, "label": label, "kind": kind,
                        "caption": " ".join(b[4].split())[:300], "w": pm.width, "h": pm.height})
    return figures


def _embedded_figures(page, page_no: int, assets: Path, min_fig_px: int, zoom: float = 2.0) -> list[dict]:
    """Fallback for caption-less pages: clip-render *clustered* embedded-image regions, so a
    diagram split into many small images becomes one figure rather than dozens of fragments."""
    import fitz
    rects = []
    for img in page.get_images(full=True):
        try:
            rects += [[r.x0, r.y0, r.x1, r.y1] for r in page.get_image_rects(img[0])]
        except Exception:  # noqa: BLE001
            pass
    rects = [r for r in rects if r[2] - r[0] > 1 and r[3] - r[1] > 1]
    if not rects:
        return []
    pr = page.rect
    figures = []
    for i, c in enumerate(_cluster_rects(rects), 1):
        if (c[2] - c[0]) * zoom < min_fig_px or (c[3] - c[1]) * zoom < min_fig_px:
            continue
        clip = fitz.Rect(max(pr.x0, c[0] - 4), max(pr.y0, c[1] - 4),
                         min(pr.x1, c[2] + 4), min(pr.y1, c[3] + 4))
        pm = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=clip)
        fname = f"fig_p{page_no}_img{i}.png"
        pm.save(str(assets / fname))
        figures.append({"file": fname, "page": page_no, "kind": "image", "w": pm.width, "h": pm.height})
    return figures


def parse(pdf_path: str, out_dir: str, min_fig_px: int = 80) -> dict:
    import fitz  # PyMuPDF — lazy so text-only sources don't load it

    pdf_path = str(Path(pdf_path).expanduser())
    out = Path(out_dir)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    pages, figures = [], []
    for i, page in enumerate(doc):
        page_no = i + 1
        text = page.get_text("text")
        pages.append({"page": page_no, "n_chars": len(text), "text": text})
        page_figs = _clip_figures(page, page_no, assets, min_fig_px)
        if not page_figs:  # no captions matched -> clustered embedded-image fallback
            page_figs = _embedded_figures(page, page_no, assets, min_fig_px)
        figures.extend(page_figs)

    manifest = {
        "pdf": pdf_path,
        "title": doc.metadata.get("title") or Path(pdf_path).stem,
        "n_pages": doc.page_count,
        "pages": pages,
        "figures": figures,
        "assets_dir": str(assets),
    }
    (out / "parse.json").write_text(json.dumps(manifest, indent=2))
    return manifest


_IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*<?([^)>\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)[\"']")


def parse_text(src_path: str, out_dir: str) -> dict:
    """Ingest a markdown/text/HTML file directly (no PDF round-trip). The whole document
    is one "page"; locally-referenced images (markdown ![](path) / <img src>) are copied
    into assets/ so the `figure` component can use them by filename."""
    src = Path(src_path).expanduser()
    out = Path(out_dir)
    assets = out / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8", errors="replace")

    figures, seen = [], set()
    for i, m in enumerate(_IMG_RE.finditer(text), 1):
        ref = m.group(1) or m.group(2)
        if not ref or ref in seen or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", ref):
            continue  # skip dups and remote URLs (data:/http(s):// etc.)
        seen.add(ref)
        img = (src.parent / ref).expanduser()
        if img.is_file():
            fname = f"fig_{i}_{img.stem}{img.suffix.lower() or '.png'}"
            shutil.copy2(img, assets / fname)
            figures.append({"file": fname, "page": 1, "ref": ref})

    manifest = {
        "source": str(src),
        "pdf": str(src),  # back-compat: planners/summary read either key
        "title": src.stem,
        "n_pages": 1,
        "pages": [{"page": 1, "n_chars": len(text), "text": text}],
        "figures": figures,
        "assets_dir": str(assets),
    }
    (out / "parse.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def summarize(manifest: dict) -> str:
    figs = manifest["figures"]
    lines = [
        f"Parsed: {manifest.get('source') or manifest.get('pdf')}",
        f"  pages: {manifest['n_pages']} | total chars: {sum(p['n_chars'] for p in manifest['pages'])}",
        f"  figures ({len(figs)}):",
    ]
    for f in figs:
        cap = f.get("caption", "")
        cap = f" — {cap[:80]}{'…' if len(cap) > 80 else ''}" if cap else ""
        lines.append(f"    {f.get('label') or f['file']} [{f['file']}, p{f['page']}]{cap}")
    if not figs:
        lines.append("    none")
    lines.append(f"  assets dir: {manifest['assets_dir']}")
    return "\n".join(lines)
