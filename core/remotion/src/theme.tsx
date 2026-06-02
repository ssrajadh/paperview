import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

export const C = {
  bg0: "#0a0e1f",
  bg1: "#161d3d",
  text: "#eef1ff",
  dim: "#9aa3c7",
  accent: "#ffd166",
  good: "#4ade80",
  bad: "#fb7185",
  blue: "#5ea0ff",
  purple: "#c084fc",
  card: "#ffffff",
  line: "rgba(255,255,255,0.13)",
};

export const FONT =
  'Inter, system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif';
export const MONO = '"SF Mono", ui-monospace, Menlo, Consolas, monospace';

// pure animation helpers (frame is read once per component and passed in)
export const fade = (f: number, s: number, d = 15) =>
  interpolate(f, [s, s + d], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
export const rise = (f: number, s: number, d = 18, px = 26) =>
  interpolate(f, [s, s + d], [px, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const NODES = [
  [8, 18], [22, 70], [15, 44], [34, 25], [30, 88], [46, 58], [52, 12],
  [63, 80], [70, 38], [78, 66], [86, 22], [90, 50], [58, 35], [40, 46],
  [73, 90], [12, 88],
];
const EDGES = [
  [0, 2], [2, 3], [3, 13], [13, 5], [5, 8], [8, 9], [9, 11], [11, 10],
  [12, 6], [12, 8], [1, 2], [1, 4], [4, 5], [7, 9], [7, 14], [10, 11],
  [6, 10], [13, 12], [3, 6], [0, 15], [15, 1],
];

// Soft "aurora" glow blobs that drift on EVERY scene so nothing is ever fully
// static. Frame-driven (deterministic — no RNG), low opacity, well behind content.
const BLOBS: [string, number, number][] = [
  ["rgba(94,160,255,0.22)", 28, 30], // blue
  ["rgba(192,132,252,0.18)", 74, 62], // purple
  ["rgba(74,222,128,0.10)", 52, 90], // faint green
];

/** Ambient backdrop, present on every scene: a dark radial base + slowly drifting
 *  glow + a vignette (reads "intentionally dark", not black). `graph` adds the
 *  dense drifting attention-graph layer used by title/outro. */
export const Background: React.FC<{ graph?: boolean }> = ({ graph = false }) => {
  const frame = useCurrentFrame();
  const drift = (i: number, a: number) => Math.sin(frame * 0.012 + i * 1.7 + a * 2.1) * 1.4;
  const pts = NODES.map(([x, y], i) => [x + drift(i, 0), y + drift(i, 1)]);
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1500px 1000px at 50% 34%, ${C.bg1} 0%, ${C.bg0} 70%)`,
        overflow: "hidden",
      }}
    >
      {BLOBS.map(([hue, bx, by], i) => {
        const x = bx + Math.sin(frame * 0.008 + i * 2.1) * 6;
        const y = by + Math.cos(frame * 0.0065 + i * 1.3) * 5;
        const s = 1 + Math.sin(frame * 0.01 + i) * 0.06;
        return (
          <div key={i} style={{
            position: "absolute", left: `${x}%`, top: `${y}%`, width: 1200, height: 1200,
            transform: `translate(-50%,-50%) scale(${s})`,
            background: `radial-gradient(circle, ${hue} 0%, rgba(0,0,0,0) 60%)`,
            filter: "blur(40px)",
          }} />
        );
      })}
      {graph && (
        <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"
          style={{ position: "absolute", inset: 0, opacity: 0.5 }}>
          {EDGES.map(([a, b], i) => (
            <line key={i} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]}
              stroke="rgba(120,150,255,0.18)" strokeWidth={0.12} />
          ))}
          {pts.map(([x, y], i) => (
            <circle key={i} cx={x} cy={y} r={0.45} fill="rgba(150,180,255,0.55)" />
          ))}
        </svg>
      )}
      {/* vignette — darkens the edges so content reads as deliberately framed */}
      <AbsoluteFill style={{
        background: "radial-gradient(125% 125% at 50% 45%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.45) 100%)",
        pointerEvents: "none",
      }} />
    </AbsoluteFill>
  );
};

/** White rounded card to hold transparent-background figure PNGs / equations. */
export const Card: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({
  children, style,
}) => (
  <div style={{
    background: C.card, borderRadius: 24, boxShadow: "0 30px 80px rgba(0,0,0,0.45)",
    padding: 28, display: "flex", alignItems: "center", justifyContent: "center", ...style,
  }}>
    {children}
  </div>
);

/** Optional scene heading (top), used by several components. */
export const Heading: React.FC<{ children: React.ReactNode; frame: number }> = ({ children, frame }) => (
  <div style={{
    position: "absolute", top: 70, width: "100%", textAlign: "center", color: C.text,
    fontSize: 58, fontWeight: 800, letterSpacing: -1,
    opacity: fade(frame, 4, 16), transform: `translateY(${rise(frame, 4)}px)`,
  }}>
    {children}
  </div>
);
