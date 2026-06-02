import React from "react";
import {
  AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig,
} from "remotion";
import katex from "katex";
import "katex/dist/katex.min.css";
import { Background, Card, Heading, C, FONT, MONO, fade, rise } from "../theme";

const base: React.CSSProperties = { fontFamily: FONT };

// ---------------- title ----------------
export const Title: React.FC<any> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14, stiffness: 90, mass: 0.9 } });
  return (
    <AbsoluteFill style={base}>
      <Background graph />
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
            <Img src={staticFile(`assets/${src}`)} style={{ height: imgH, width: "auto", maxWidth: "82vw" }} />
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
      <Background graph />
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

export const REGISTRY: Record<string, React.FC<any>> = {
  title: Title, statement: Statement, bullets: Bullets, figure: Figure,
  equation: Equation, comparison: Comparison, stats: Stats, outro: Outro,
};
