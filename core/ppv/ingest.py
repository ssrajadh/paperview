"""PDF ingest: per-page text + extracted figures. (v1: embedded raster figures only;
vector-figure clip-rendering is future work — see docs/PAPERVIEW_V1.md D2.)"""
from __future__ import annotations
import json
import os
from pathlib import Path

import fitz  # PyMuPDF


def parse(pdf_path: str, out_dir: str, min_fig_px: int = 80) -> dict:
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


def summarize(manifest: dict) -> str:
    figs = manifest["figures"]
    lines = [
        f"Parsed: {manifest['pdf']}",
        f"  pages: {manifest['n_pages']} | total chars: {sum(p['n_chars'] for p in manifest['pages'])}",
        f"  figures extracted ({len(figs)}): " + (", ".join(f["file"] for f in figs) or "none"),
        f"  assets dir: {manifest['assets_dir']}",
    ]
    return "\n".join(lines)
