"""Source ingest -> parse.json (per-"page" text + figures in assets/). PDFs go through
PyMuPDF (embedded raster figures only; vector figures are future work — D2). Markdown/
text/HTML are read directly (no PDF round-trip) and local image refs are copied into
assets/. All sources emit the same manifest shape so the planner is source-agnostic."""
from __future__ import annotations
import json
import re
import shutil
from pathlib import Path

TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text", ".rst", ".html", ".htm", ".tex"}


def parse_source(src: str, out_dir: str) -> dict:
    """Dispatch on file type: PDF -> PyMuPDF; markdown/text/HTML -> read directly."""
    if Path(src).expanduser().suffix.lower() == ".pdf":
        return parse(src, out_dir)
    return parse_text(src, out_dir)


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
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                pm = fitz.Pixmap(doc, xref)
                if pm.width < min_fig_px or pm.height < min_fig_px:
                    continue
                if pm.n - pm.alpha >= 4:  # CMYK -> RGB
                    pm = fitz.Pixmap(fitz.csRGB, pm)
                fname = f"fig_p{page_no}_{xref}.png"
                pm.save(str(assets / fname))
                figures.append({"file": fname, "page": page_no, "w": pm.width, "h": pm.height})
            except Exception as e:  # noqa: BLE001 -- MVP: skip unextractable images
                print(f"  ! page {page_no} image xref {xref} skipped: {e}")

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
        f"  figures ({len(figs)}): " + (", ".join(f["file"] for f in figs) or "none"),
        f"  assets dir: {manifest['assets_dir']}",
    ]
    return "\n".join(lines)
