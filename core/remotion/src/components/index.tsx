import React, { useEffect, useState } from "react";
import {
  AbsoluteFill, Img, cancelRender, continueRender, delayRender, interpolate, spring,
  staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import katex from "katex";
import "katex/dist/katex.min.css";
import { Highlight, themes } from "prism-react-renderer";
import mermaid from "mermaid";
import { Background, Card, Heading, C, FONT, MONO, fade, rise } from "../theme";

// Mermaid is configured once at module load: no auto-start (we render on demand), and
// deterministic ids so every frame/worker produces byte-identical SVG markup (a render must
// look the same everywhere — see notes D5/D12). Instead of mermaid's stock `neutral` theme on a
// white card (which looks like a figure photocopied out of a paper — gray boxes, black arrows,
// foreign to our dark glowy backdrops), we drive mermaid's `base` theme with our OWN palette so
// the diagram reads as native video: deep-blue glass nodes, light text, soft edges. These colors
// are the shared content palette (legible on all three themes), matching the design rule that
// content colors stay constant across midnight/slate/dusk.
mermaid.initialize({
  startOnLoad: false,
  theme: "base",
  securityLevel: "loose",
  deterministicIds: true,
  deterministicIDSeed: "paperview",
  fontFamily: FONT,
  flowchart: { curve: "basis", nodeSpacing: 48, rankSpacing: 56, padding: 14, htmlLabels: true },
  themeVariables: {
    darkMode: true,
    background: "#0d1430",
    fontFamily: FONT,
    fontSize: "21px",
    // flowchart / generic nodes — deep-blue glass with a blue glow border + light label
    primaryColor: "#1b2748",
    primaryTextColor: C.text,
    primaryBorderColor: C.blue,
    secondaryColor: "#241a44",
    secondaryTextColor: C.text,
    secondaryBorderColor: C.purple,
    tertiaryColor: "#13203b",
    tertiaryTextColor: C.text,
    tertiaryBorderColor: "rgba(255,255,255,0.22)",
    mainBkg: "#1b2748",
    nodeBorder: C.blue,
    nodeTextColor: C.text,
    textColor: C.text,
    lineColor: C.dim,
    titleColor: C.text,
    // subgraph clusters — faint glass, no stark fills
    clusterBkg: "rgba(255,255,255,0.04)",
    clusterBorder: "rgba(255,255,255,0.18)",
    // edge labels must not paint white boxes over a dark backdrop
    edgeLabelBackground: "#101a36",
    labelBackground: "#101a36",
    // sequence diagrams
    actorBkg: "#1b2748",
    actorBorder: C.blue,
    actorTextColor: C.text,
    actorLineColor: C.dim,
    signalColor: C.dim,
    signalTextColor: C.text,
    labelBoxBkgColor: "#1b2748",
    labelBoxBorderColor: C.blue,
    labelTextColor: C.text,
    loopTextColor: C.text,
    activationBkgColor: "#241a44",
    activationBorderColor: C.purple,
    noteBkgColor: "#241a44",
    noteTextColor: C.text,
    noteBorderColor: C.purple,
  },
});

const base: React.CSSProperties = { fontFamily: FONT };

// Dark translucent "glass" surface for diagrams — the dark-theme counterpart to the white Card.
// A faint fill + hairline border + outer shadow give the panel definition over the themed
// backdrop without the stark white-sheet look that made mermaid diagrams read as pasted figures.
const GLASS: React.CSSProperties = {
  background: "rgba(255,255,255,0.035)", border: "1px solid rgba(255,255,255,0.10)",
  borderRadius: 24, padding: 44, maxWidth: "88vw",
  boxShadow: "0 30px 80px rgba(0,0,0,0.40), inset 0 1px 0 rgba(255,255,255,0.06)",
  display: "flex", alignItems: "center", justifyContent: "center",
};

// ---------------- title ----------------
export const Title: React.FC<any> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14, stiffness: 90, mass: 0.9 } });
  return (
    <AbsoluteFill style={base}>
      <Background hero />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 90, textAlign: "center" }}>
        <div style={{ transform: `scale(${interpolate(s, [0, 1], [0.82, 1])})`, opacity: s, color: C.text,
          fontSize: 116, fontWeight: 900, letterSpacing: -3, lineHeight: 1.04,
          textShadow: "0 10px 60px rgba(94,160,255,0.4)" }}>{title}</div>
        {subtitle && (
          <div style={{ opacity: fade(frame, 28, 22), color: C.dim, fontSize: 40, marginTop: 44 }}>{subtitle}</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- statement ----------------
export const Statement: React.FC<any> = ({ text, eyebrow }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={base}>
      <Background />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 140, textAlign: "center" }}>
        {eyebrow && (
          <div style={{ opacity: fade(frame, 2, 12), color: C.accent, fontSize: 32, fontWeight: 800,
            letterSpacing: 3, textTransform: "uppercase", marginBottom: 28 }}>{eyebrow}</div>
        )}
        <div style={{ opacity: fade(frame, 8, 18), transform: `translateY(${rise(frame, 8, 20, 30)}px)`,
          color: C.text, fontSize: 72, fontWeight: 800, lineHeight: 1.18, maxWidth: 1500 }}>{text}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- bullets ----------------
export const Bullets: React.FC<any> = ({ heading, items = [] }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={base}>
      <Background />
      {heading && <Heading frame={frame}>{heading}</Heading>}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "flex-start", padding: "0 220px",
        paddingTop: heading ? 80 : 0 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 36 }}>
          {items.map((it: string, i: number) => {
            const at = 14 + i * 14;
            return (
              <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 26,
                opacity: fade(frame, at, 12), transform: `translateX(${rise(frame, at, 12, -26)}px)` }}>
                <div style={{ width: 18, height: 18, borderRadius: 6, marginTop: 18, flexShrink: 0,
                  background: C.blue, boxShadow: "0 0 24px rgba(94,160,255,0.6)" }} />
                <div style={{ color: C.text, fontSize: 50, fontWeight: 600, lineHeight: 1.3 }}>{it}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- figure ----------------
export const Figure: React.FC<any> = ({ src, caption, label }) => {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const imgH = (caption ? 0.62 : 0.7) * height;
  return (
    <AbsoluteFill style={base}>
      <Background />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 70 }}>
        <div style={{ position: "relative", opacity: fade(frame, 8, 16), transform: `translateY(${rise(frame, 8, 18, 28)}px)` }}>
          <Card>
            {/* cap BOTH dimensions with auto width/height so the browser preserves aspect
                ratio — a fixed height + maxWidth would clamp width and squish wide figures. */}
            <Img src={staticFile(`assets/${src}`)}
              style={{ maxHeight: imgH, maxWidth: "84vw", width: "auto", height: "auto" }} />
          </Card>
          {label && (
            <div style={{ position: "absolute", top: -22, left: 36, background: C.accent, color: "#0a0e1f",
              fontSize: 28, fontWeight: 800, padding: "8px 20px", borderRadius: 12 }}>{label}</div>
          )}
        </div>
        {caption && (
          <div style={{ opacity: fade(frame, 24, 16), color: C.dim, fontSize: 34, marginTop: 30,
            textAlign: "center", maxWidth: 1500 }}>{caption}</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- equation (KaTeX) ----------------
export const Equation: React.FC<any> = ({ tex, heading, caption }) => {
  const frame = useCurrentFrame();
  let html = "";
  try {
    html = katex.renderToString(String(tex ?? ""), { displayMode: true, throwOnError: false });
  } catch {
    html = `<code>${tex}</code>`;
  }
  return (
    <AbsoluteFill style={base}>
      <Background />
      {heading && <Heading frame={frame}>{heading}</Heading>}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 80, flexDirection: "column" }}>
        <div style={{ opacity: fade(frame, 10, 18), transform: `scale(${interpolate(fade(frame, 10, 18), [0, 1], [0.92, 1])})` }}>
          <Card style={{ padding: "44px 64px" }}>
            <div style={{ color: "#0a0e1f", fontSize: 60 }} dangerouslySetInnerHTML={{ __html: html }} />
          </Card>
        </div>
        {caption && (
          <div style={{ opacity: fade(frame, 30, 16), color: C.dim, fontSize: 34, marginTop: 36,
            textAlign: "center", maxWidth: 1500 }}>{caption}</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- code ----------------
// A dark "editor" panel for source snippets — built for codebase walkthroughs, not just
// paper listings. `lang` drives Prism syntax colors (omit / "text" => plain monospace, which
// suits pseudocode). `filename` shows a title bar, line numbers are always on, and
// `highlightLines` (1-based) tints lines so narration can point at them. Font auto-fits the
// snippet so a 6-liner and a 16-liner both read well. Deterministic: Prism is pure tokenizing.
// `diff` mode: each line is expected to begin with a `+`/`-`/space marker (unified-diff style);
// the marker is stripped from the code, shown as a green/red sign in the gutter, and tints the
// line — for before/after walkthroughs. In diff mode the marker replaces the line-number gutter
// and overrides `highlightLines`.
export const Code: React.FC<any> = ({ code = "", lang = "text", heading, caption, filename,
  highlightLines = [], startLine = 1, diff = false }) => {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const raw = String(code).replace(/\s+$/, "");           // drop trailing blank lines
  const rawLines = raw.split("\n");
  // diff: remember each line's +/-/context sign, then strip one leading marker so Prism
  // tokenizes the real code (a leading '+'/'-' would otherwise mis-highlight the line).
  const signs = diff ? rawLines.map((l) => (l[0] === "+" ? 1 : l[0] === "-" ? -1 : 0)) : [];
  const lines = diff ? rawLines.map((l) => l.replace(/^[+\- ]/, "")) : rawLines;
  const src = lines.join("\n");
  const longest = lines.reduce((m, l) => Math.max(m, l.length), 0);
  const hot = new Set<number>((highlightLines || []).map(Number));

  // auto-fit: cap by the panel's height (line count) AND width (longest line), then clamp.
  const maxH = 0.66 * height, maxW = 1480;
  const gutter = String(startLine + lines.length - 1).length;  // digits in the largest line no.
  const byH = maxH / (lines.length * 1.5);
  const byW = maxW / ((longest + gutter + 3) * 0.62);
  const fs = Math.max(18, Math.min(40, byH, byW));
  const lh = Math.round(fs * 1.5);

  return (
    <AbsoluteFill style={base}>
      <Background />
      {heading && <Heading frame={frame}>{heading}</Heading>}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 70,
        paddingTop: heading ? 150 : 70, flexDirection: "column" }}>
        <div style={{ opacity: fade(frame, 8, 16), transform: `translateY(${rise(frame, 8, 18, 26)}px)`,
          width: "fit-content", maxWidth: "92vw", borderRadius: 18, overflow: "hidden",
          background: "#0c1124", border: `1px solid ${C.line}`, boxShadow: "0 30px 80px rgba(0,0,0,0.5)" }}>
          {/* title bar: traffic-light dots + filename (editor feel) */}
          <div style={{ display: "flex", alignItems: "center", gap: 18, padding: "16px 26px",
            background: "rgba(255,255,255,0.04)", borderBottom: `1px solid ${C.line}` }}>
            <div style={{ display: "flex", gap: 10 }}>
              {[C.bad, C.accent, C.good].map((c) => (
                <div key={c} style={{ width: 15, height: 15, borderRadius: "50%", background: c, opacity: 0.85 }} />
              ))}
            </div>
            {filename && <div style={{ fontFamily: MONO, fontSize: 26, color: C.dim, marginLeft: 8 }}>{filename}</div>}
          </div>
          {/* code body */}
          <Highlight code={src} language={lang} theme={themes.nightOwl}>
            {({ tokens, getLineProps, getTokenProps }) => (
              <div style={{ fontFamily: MONO, fontSize: fs, lineHeight: `${lh}px`, padding: "22px 0" }}>
                {tokens.map((line, i) => {
                  const lp = getLineProps({ line });
                  const sign = diff ? signs[i] : 0;
                  const isHot = !diff && hot.has(startLine + i);
                  const tint = sign > 0 ? "rgba(74,222,128,0.15)" : sign < 0 ? "rgba(251,113,133,0.15)"
                    : isHot ? "rgba(255,209,102,0.13)" : "transparent";
                  const edge = sign > 0 ? C.good : sign < 0 ? C.bad : isHot ? C.accent : "transparent";
                  const gutterColor = sign > 0 ? C.good : sign < 0 ? C.bad : C.dim;
                  return (
                    <div key={i} {...lp} style={{ ...lp.style, display: "flex",
                      background: tint,
                      borderLeft: `4px solid ${edge}`,
                      padding: "0 30px 0 26px" }}>
                      <span style={{ display: "inline-block", width: `${gutter + 1}ch`, textAlign: "right",
                        marginRight: 28, color: gutterColor, opacity: isHot || sign ? 0.9 : 0.45, userSelect: "none" }}>
                        {diff ? (sign > 0 ? "+" : sign < 0 ? "−" : "") : startLine + i}
                      </span>
                      <span style={{ whiteSpace: "pre" }}>
                        {line.map((token, k) => {
                          const tp = getTokenProps({ token });
                          return <span key={k} {...tp} />;
                        })}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </Highlight>
        </div>
        {caption && (
          <div style={{ opacity: fade(frame, 28, 16), color: C.dim, fontSize: 32, marginTop: 28,
            textAlign: "center", maxWidth: 1500 }}>{caption}</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- mermaid (diagrams) ----------------
// Render a Mermaid diagram (flowchart / sequence / state / class / ER / etc.) to SVG at render
// time in headless Chrome, then inline it on a dark glass panel themed to match the video (see
// the mermaid.initialize palette above). `code` is the Mermaid source. For
// architecture / data-flow / state diagrams in BOTH papers and codebases, where no real figure
// exists to extract. delayRender holds the frame until the async render resolves; a syntax error
// degrades to the raw source + message (one bad diagram never kills the whole render). The
// module-load config keeps the SVG deterministic.
export const Mermaid: React.FC<any> = ({ code = "", heading, caption }) => {
  const frame = useCurrentFrame();
  const { height } = useVideoConfig();
  const [handle] = useState(() => delayRender("mermaid"));
  const [svg, setSvg] = useState("");
  const [err, setErr] = useState("");
  useEffect(() => {
    let live = true;
    mermaid
      .render("ppv-mermaid", String(code).trim() || "graph TD; A;")
      .then(({ svg }) => {
        // Strip the root svg's width/height attributes + inline max-width so the viewBox is the
        // only size source: the svg then has an intrinsic aspect and our scoped CSS scales it to
        // fit the card (like the Img trick). Left intact, mermaid's width="100%" resolves against
        // the shrink-wrapped flex parent → ~0, collapsing the diagram.
        const cleaned = svg
          .replace(/(<svg[^>]*?)\s(?:width|height)="[^"]*"/g, "$1")
          .replace(/max-width:\s*[\d.]+px;?/g, "");
        if (live) { setSvg(cleaned); continueRender(handle); }
      })
      .catch((e) => { if (live) { setErr(String(e?.message ?? e)); continueRender(handle); } });
    return () => { live = false; };
  }, [code, handle]);
  // Fill the frame: diagrams are usually height-bound (tall flow/sequence graphs leave the sides
  // empty), so give them most of the vertical space and a near-full-width panel — the SVG scales to
  // fit this box, so a bigger box is the only real lever on node/text size at 1080p.
  const maxH = (caption ? 0.68 : 0.82) * height;
  return (
    <AbsoluteFill style={base}>
      <Background />
      {heading && <Heading frame={frame}>{heading}</Heading>}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 48,
        paddingTop: heading ? 120 : 48, flexDirection: "column" }}>
        <div style={{ opacity: fade(frame, 8, 16), transform: `translateY(${rise(frame, 8, 18, 28)}px)` }}>
          {err ? (
            <div style={GLASS}>
              <div style={{ fontFamily: MONO, color: C.bad, fontSize: 26, whiteSpace: "pre-wrap" }}>
                mermaid error: {err}
              </div>
            </div>
          ) : (
            // The diagram sits on a faint dark "glass" panel (not a white card): a subtle drop
            // shadow under each node lifts it off the backdrop so it feels lit/native, not a flat
            // pasted figure. Edge-label boxes get the panel's tint so no white chips show through.
            <div style={{ ...GLASS, padding: 32, maxWidth: "95vw" }}>
              <style>{`.ppv-mmd svg { display: block; margin: auto; width: auto; height: auto;
                max-width: 100%; max-height: ${Math.round(maxH)}px; }
                .ppv-mmd .node rect, .ppv-mmd .node circle, .ppv-mmd .node polygon,
                .ppv-mmd .node path, .ppv-mmd .actor, .ppv-mmd .cluster rect {
                  filter: drop-shadow(0 6px 16px rgba(0,0,0,0.45)); }
                .ppv-mmd .edgeLabel, .ppv-mmd .edgeLabel p { background: transparent !important;
                  color: ${C.text} !important; }`}</style>
              <div className="ppv-mmd" style={{ display: "flex", justifyContent: "center",
                width: "92vw", maxWidth: 1780 }}
                dangerouslySetInnerHTML={{ __html: svg }} />
            </div>
          )}
        </div>
        {caption && (
          <div style={{ opacity: fade(frame, 24, 16), color: C.dim, fontSize: 34, marginTop: 30,
            textAlign: "center", maxWidth: 1500 }}>{caption}</div>
        )}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- comparison ----------------
export const Comparison: React.FC<any> = ({ heading, rowLabels = [], columns = [] }) => {
  const frame = useCurrentFrame();
  const cols = columns.length;
  return (
    <AbsoluteFill style={base}>
      <Background />
      {heading && <Heading frame={frame}>{heading}</Heading>}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", paddingTop: heading ? 60 : 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: `420px ${"320px ".repeat(cols)}`.trim(), gap: 18, alignItems: "center" }}>
          <div />
          {columns.map((c: any, j: number) => (
            <div key={j} style={{ textAlign: "center", fontSize: 38, fontWeight: 800,
              color: c.highlight ? C.good : C.dim, opacity: fade(frame, 10, 12) }}>{c.title}</div>
          ))}
          {rowLabels.map((rl: string, i: number) => (
            <React.Fragment key={i}>
              <div style={{ color: C.text, fontSize: 34, opacity: fade(frame, 24 + i * 14, 12),
                transform: `translateX(${rise(frame, 24 + i * 14, 12, -30)}px)` }}>{rl}</div>
              {columns.map((c: any, j: number) => (
                <div key={j} style={{ opacity: fade(frame, 30 + i * 14, 12) }}>
                  <div style={{ borderRadius: 14, padding: "16px 0", textAlign: "center", fontSize: 34,
                    fontWeight: 800, fontFamily: MONO,
                    color: c.highlight ? C.good : C.dim,
                    background: c.highlight ? "rgba(74,222,128,0.16)" : "rgba(255,255,255,0.05)",
                    border: `2px solid ${c.highlight ? C.good : C.line}`,
                    boxShadow: c.highlight ? "0 0 30px rgba(74,222,128,0.22)" : "none" }}>
                    {(c.values || [])[i]}
                  </div>
                </div>
              ))}
            </React.Fragment>
          ))}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- stats ----------------
export const Stats: React.FC<any> = ({ heading, items = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={base}>
      <Background />
      {heading && <Heading frame={frame}>{heading}</Heading>}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", flexDirection: "row", gap: 44, padding: 80 }}>
        {items.map((it: any, i: number) => {
          const s = spring({ frame: frame - (10 + i * 16), fps, config: { damping: 12, stiffness: 90 } });
          const hot = it.highlight;
          return (
            <div key={i} style={{ transform: `scale(${interpolate(s, [0, 1], [0.6, 1])})`, opacity: s,
              background: hot ? "rgba(255,209,102,0.12)" : "rgba(94,160,255,0.10)",
              border: `2px solid ${hot ? C.accent : C.blue}`, borderRadius: 24, padding: "40px 48px",
              textAlign: "center", minWidth: 320, boxShadow: hot ? "0 0 50px rgba(255,209,102,0.3)" : "none" }}>
              <div style={{ color: hot ? C.accent : C.text, fontSize: 84, fontWeight: 900, fontFamily: MONO }}>{it.value}</div>
              <div style={{ color: C.dim, fontSize: 30, marginTop: 10 }}>{it.label}</div>
            </div>
          );
        })}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- outro ----------------
export const Outro: React.FC<any> = ({ text, tags = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const placed: [string, number, number][] = tags.map((t: string, i: number) => {
    const angle = (i / Math.max(tags.length, 1)) * Math.PI * 2;
    return [t, 50 + Math.cos(angle) * 30, 42 + Math.sin(angle) * 26];
  });
  const phrase = spring({ frame: frame - 70, fps, config: { damping: 14, stiffness: 80 } });
  return (
    <AbsoluteFill style={base}>
      <Background hero />
      {placed.map(([t, x, y], i) => {
        const op = interpolate(frame, [16 + i * 7, 40 + i * 7, 70, 95], [0, 0.8, 0.8, 0],
          { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        return (
          <div key={i} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, transform: "translate(-50%,-50%)",
            color: C.dim, fontSize: 40, fontWeight: 700, opacity: op }}>{t}</div>
        );
      })}
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 120 }}>
        <div style={{ opacity: phrase, transform: `scale(${interpolate(phrase, [0, 1], [0.85, 1])})`,
          color: C.text, fontSize: 86, fontWeight: 900, textAlign: "center",
          textShadow: "0 10px 60px rgba(94,160,255,0.45)" }}>{text}</div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------- caption overlay (opt-in subtitles) ----------------
/** A subtitle bar showing the scene's narration verbatim, pinned to the bottom. Opt-in
 *  via meta.captions / `ppv render --captions`. Rendered inside each scene's sequence so
 *  it fades with the cross-fade and is timed to that scene. */
export const Caption: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  if (!text) return null;
  return (
    <AbsoluteFill style={{ ...base, justifyContent: "flex-end", alignItems: "center",
      padding: "0 200px 64px", pointerEvents: "none" }}>
      <div style={{ opacity: fade(frame, 2, 8), maxWidth: 1480, textAlign: "center",
        background: "rgba(8,11,26,0.72)", color: C.text, fontSize: 34, fontWeight: 600,
        lineHeight: 1.32, padding: "16px 30px", borderRadius: 14,
        border: `1px solid ${C.line}`, backdropFilter: "blur(4px)" }}>{text}</div>
    </AbsoluteFill>
  );
};

export const REGISTRY: Record<string, React.FC<any>> = {
  title: Title, statement: Statement, bullets: Bullets, figure: Figure,
  equation: Equation, code: Code, mermaid: Mermaid, comparison: Comparison,
  stats: Stats, outro: Outro,
};
