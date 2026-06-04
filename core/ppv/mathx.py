"""Real equation extraction from arXiv LaTeX source (D1) — the fidelity differentiator.

The planner otherwise typesets equations from the model's *memory* of the paper, which is
the validated faithfulness risk on unfamiliar papers. When the paper is on arXiv we can do
better: fetch its LaTeX e-print and pull the actual display equations verbatim, so the math
on screen is the paper's own. Custom no-arg macros are expanded so the emitted TeX renders
in KaTeX as-is; the surrounding sentence is captured as `context` to help the planner place
each equation. Papers not on arXiv get a clear "transcribe from the PDF" message (graceful).
"""
from __future__ import annotations
import gzip
import io
import json
import re
import tarfile
import urllib.request
from pathlib import Path

ARXIV_ID = re.compile(r"arxiv\.org/(?:abs|pdf|e-print)/(\d{4}\.\d{4,5})", re.I)
ARXIV_TAG = re.compile(r"arXiv:\s*(\d{4}\.\d{4,5})", re.I)
BARE_ID = re.compile(r"^(\d{4}\.\d{4,5})(v\d+)?$")

# display-math environments worth lifting (numbered or not)
_ENVS = ["equation", "align", "gather", "multline", "eqnarray", "displaymath"]
_ENV_RE = re.compile(r"\\begin\{(" + "|".join(_ENVS) + r")\*?\}(.*?)\\end\{\1\*?\}", re.S)
_BRACKET_RE = re.compile(r"\\\[(.*?)\\\]", re.S)
_DOLLAR_RE = re.compile(r"(?<!\\)\$\$(.+?)\$\$", re.S)
_LABEL_RE = re.compile(r"\\label\{([^}]*)\}")


def find_arxiv_id(text: str) -> str | None:
    """Pull an arXiv id from a URL, an 'arXiv:' tag, or a bare id string."""
    for rx in (ARXIV_ID, ARXIV_TAG):
        m = rx.search(text)
        if m:
            return m.group(1)
    m = BARE_ID.match(text.strip())
    return m.group(1) if m else None


def fetch_eprint(arxiv_id: str, timeout: float = 30.0) -> str:
    """Download an arXiv e-print and return its concatenated .tex source. The endpoint
    returns a gzipped tar (multi-file) or a single gzipped .tex; handle both."""
    url = f"https://arxiv.org/e-print/{arxiv_id}"
    req = urllib.request.Request(url, headers={"User-Agent": "paperview/0.1 (ppv math)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    # try tar (possibly gz-compressed); fall back to a single gz'd file
    try:
        with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
            parts = []
            for m in tf.getmembers():
                if m.isfile() and m.name.lower().endswith(".tex"):
                    parts.append(tf.extractfile(m).read().decode("utf-8", "replace"))
            if parts:
                return "\n".join(parts)
    except tarfile.TarError:
        pass
    try:
        return gzip.decompress(raw).decode("utf-8", "replace")
    except OSError:
        return raw.decode("utf-8", "replace")


def _strip_comments(tex: str) -> str:
    # drop TeX comments (unescaped %) without touching \%
    return re.sub(r"(?<!\\)%.*", "", tex)


def _read_group(s: str, k: int) -> tuple[str | None, int]:
    """If s[k] == '{', return (inner text, index just past the matching '}'); else (None, k)."""
    if k >= len(s) or s[k] != "{":
        return None, k
    depth = 0
    for i in range(k, len(s)):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[k + 1:i], i + 1
    return None, len(s)


def _balanced(s: str, open_idx: int) -> str | None:
    return _read_group(s, open_idx)[0]


def _collect_macros(tex: str) -> dict[str, tuple[int, str]]:
    """\\newcommand / \\def / \\DeclareMathOperator definitions -> {name: (nargs, body)}.
    Argument-taking macros are captured too (nargs from the [n] spec) so they can be
    expanded into the equations — papers lean on these custom shorthands heavily."""
    macros: dict[str, tuple[int, str]] = {}
    for m in re.finditer(r"\\(?:re)?newcommand\*?\s*\{?\s*(\\[A-Za-z]+)\s*\}?\s*(?:\[(\d+)\])?\s*\{", tex):
        body = _balanced(tex, m.end() - 1)
        if body is not None:
            macros[m.group(1)] = (int(m.group(2) or 0), body.strip())
    for m in re.finditer(r"\\DeclareMathOperator\*?\s*\{\s*(\\[A-Za-z]+)\s*\}\s*\{", tex):
        body = _balanced(tex, m.end() - 1)
        if body is not None:
            macros[m.group(1)] = (0, r"\operatorname{" + body.strip() + "}")
    for m in re.finditer(r"\\def\s*(\\[A-Za-z]+)\s*\{", tex):
        body = _balanced(tex, m.end() - 1)
        if body is not None and "#" not in body:
            macros[m.group(1)] = (0, body.strip())
    return macros


def _apply(tex: str, name: str, nargs: int, body: str) -> tuple[str, bool]:
    """Substitute every call of macro `name` (taking `nargs` brace args) in `tex`."""
    out: list[str] = []
    i, n, changed = 0, len(name), False
    while i < len(tex):
        j = tex.find(name, i)
        if j < 0:
            out.append(tex[i:]); break
        out.append(tex[i:j])
        after = j + n
        if after < len(tex) and tex[after].isalpha():  # \mc must not fire on \mce
            out.append(name); i = after; continue
        if nargs == 0:
            out.append(body); i = after; changed = True; continue
        k, args, ok = after, [], True
        for _ in range(nargs):
            while k < len(tex) and tex[k].isspace():
                k += 1
            inner, k2 = _read_group(tex, k)
            if inner is None:
                ok = False; break
            args.append(inner); k = k2
        if not ok:
            out.append(name); i = after; continue
        rep = body
        for idx, a in enumerate(args, 1):
            rep = rep.replace(f"#{idx}", a)
        out.append(rep); i = k; changed = True
    return "".join(out), changed


def _expand(tex: str, macros: dict[str, tuple[int, str]], passes: int = 5) -> str:
    """Substitute custom macros into an equation, a few passes for nested defs."""
    for _ in range(passes):
        any_changed = False
        for name, (nargs, body) in macros.items():
            tex, ch = _apply(tex, name, nargs, body)
            any_changed = any_changed or ch
        if not any_changed:
            break
    return tex


def _clean(body: str, macros: dict[str, str]) -> str:
    body = _LABEL_RE.sub("", body)
    body = re.sub(r"\\(nonumber|notag)\b", "", body)
    body = _expand(body, macros)
    body = " ".join(body.split())
    body = re.sub(r"(\\\\)\s*$", "", body).strip()  # drop a dangling row separator
    # multi-line / aligned math needs an alignment environment to render in KaTeX — but
    # don't double-wrap if the body already carries one (aligned/array/cases/split/matrix).
    has_env = re.search(r"\\begin\{(aligned|array|cases|split|[bBpvV]?matrix|gathered)\}", body)
    if re.search(r"\\\\|&", body) and not has_env:
        body = r"\begin{aligned} " + body + r" \end{aligned}"
    return body


def _context_before(tex: str, start: int) -> str:
    """The plain-text sentence fragment just before an equation, with math/markup removed,
    so the planner can tell what the equation is about (helps placement)."""
    w = tex[max(0, start - 500):start]
    w = re.sub(r"\\begin\{.*?\}.*?\\end\{.*?\}", " ", w, flags=re.S)  # prior display envs
    w = re.sub(r"\\\[.*?\\\]", " ", w, flags=re.S)
    w = re.sub(r"\$[^$]*\$", " ", w)                                   # inline math
    w = re.sub(r"\\[A-Za-z]+\*?", " ", w)                             # commands
    w = re.sub(r"[{}\\$&]", " ", w)
    w = re.sub(r"\s+", " ", w).strip()
    return w.split(". ")[-1][-160:].strip()


def extract_equations(tex: str) -> tuple[list[dict], dict]:
    """Return (equations, macros). Each equation: {tex, label?, context?}. `context` is the
    plain-text sentence fragment just before the equation, to help the planner place it."""
    tex = _strip_comments(tex)
    macros = _collect_macros(tex)
    seen: set[str] = set()
    eqs: list[dict] = []

    def add(body: str, start: int):
        label_m = _LABEL_RE.search(body)
        cleaned = _clean(body, macros)
        if len(cleaned) < 3 or cleaned in seen:
            return
        seen.add(cleaned)
        ctx = _context_before(tex, start)
        rec = {"tex": cleaned}
        if label_m:
            rec["label"] = label_m.group(1)
        if ctx:
            rec["context"] = ctx
        eqs.append(rec)

    for rx in (_ENV_RE, _BRACKET_RE, _DOLLAR_RE):
        for m in rx.finditer(tex):
            body = m.group(2) if rx is _ENV_RE else m.group(1)
            add(body, m.start())
    return eqs, macros


def extract_from_source(src: str, out_dir: str) -> dict:
    """Resolve `src` (an arXiv id/URL, or a PDF/text whose contents name one) to its arXiv
    source and write math.json with the real display equations. Returns the manifest."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    p = Path(src).expanduser()

    arxiv_id = find_arxiv_id(src)
    if arxiv_id is None and p.is_file():
        if p.suffix.lower() == ".pdf":
            import fitz
            doc = fitz.open(str(p))
            head = "".join(doc[i].get_text("text") for i in range(min(2, doc.page_count)))
            arxiv_id = find_arxiv_id(head)
        else:
            arxiv_id = find_arxiv_id(p.read_text("utf-8", "replace")[:4000])

    manifest: dict = {"source": src, "arxiv_id": arxiv_id, "equations": [], "macros": {}}
    if arxiv_id is None:
        manifest["note"] = "no arXiv id found — transcribe equations from the PDF instead"
        (out / "math.json").write_text(json.dumps(manifest, indent=2))
        return manifest

    tex = fetch_eprint(arxiv_id)
    eqs, macros = extract_equations(tex)
    manifest["equations"] = eqs
    manifest["macros"] = {k: v[1] for k, v in macros.items()}  # name -> body (reference only)
    (out / "math.json").write_text(json.dumps(manifest, indent=2))
    return manifest


def summarize_math(manifest: dict) -> str:
    if not manifest.get("arxiv_id"):
        return f"math: {manifest.get('note', 'no arXiv source')}"
    eqs = manifest["equations"]
    lines = [f"math: arXiv:{manifest['arxiv_id']} — {len(eqs)} display equations"
             f" ({len(manifest['macros'])} custom macros expanded)"]
    for e in eqs[:12]:
        lab = f" [{e['label']}]" if e.get("label") else ""
        lines.append(f"  {e['tex'][:90]}{lab}")
    if len(eqs) > 12:
        lines.append(f"  … +{len(eqs) - 12} more (see math.json)")
    return "\n".join(lines)
