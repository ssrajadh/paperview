"""Source ingest -> parse.json (per-"page" text + figures in assets/). PDF figures are
captured by clip-rendering the region around each "Figure/Table N" caption, which grabs
**vector** figures the embedded-image API misses (D2), and records the caption text too;
falls back to embedded raster on pages with no detected captions. Markdown/text/HTML are
read directly (no PDF round-trip). All sources emit the same manifest shape so the planner
is source-agnostic."""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text", ".rst", ".html", ".htm", ".tex"}

# A caption block: "Figure 3:", "Fig. 3.", "Table 3 —". The trailing separator avoids
# matching in-body reference sentences like "Table 2 summarizes our results".
_CAP_RE = re.compile(r"^\s*(figure|fig\.?|table)\s+([0-9]+)\s*[:.–—]", re.IGNORECASE)


def parse_source(src: str, out_dir: str) -> dict:
    """Dispatch on file type: PDF -> PyMuPDF; markdown/text/HTML -> read directly."""
    if Path(src).expanduser().suffix.lower() == ".pdf":
        return parse(src, out_dir)
    return parse_text(src, out_dir)


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
    if not content or len(content) > 4000:  # nothing drawn, or pathological page -> fallback
        return []

    min_pt = min_fig_px / zoom
    clusters = [c for c in _cluster_rects(content)
                if c[2] - c[0] >= min_pt and c[3] - c[1] >= min_pt]
    if not clusters:
        return []

    figures = []
    for b in blocks:
        m = _CAP_RE.match(b[4])
        if not m:
            continue
        kind = "table" if m.group(1).lower() == "table" else "figure"
        label = f"{'Table' if kind == 'table' else 'Figure'} {m.group(2)}"
        cx0, cy0, cx1, cy1 = b[:4]
        ccx, ccy = (cx0 + cx1) / 2, (cy0 + cy1) / 2
        cands = [c for c in clusters if not (c[2] < cx0 - 5 or c[0] > cx1 + 5) or c[0] <= ccx <= c[2]]
        # a figure sits above its caption, a table below — judged by cluster *center* so the
        # caption may overlap the figure's bottom edge (common when content runs to the caption)
        side = [c for c in cands if ((c[1] + c[3]) / 2 <= ccy) == (kind == "figure")]
        grp = side or cands
        if not grp:
            continue

        def vgap(c: list[float]) -> float:  # 0 if the caption is within the cluster's y-span
            return max(0.0, c[1] - ccy, ccy - c[3])
        pick = min(grp, key=vgap)
        if vgap(pick) > pr.height * 0.4:  # nearest cluster is implausibly far -> skip
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
