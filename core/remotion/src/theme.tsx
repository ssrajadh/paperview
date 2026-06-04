import React, { useContext } from "react";
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

// Soft "aurora" glow blobs that drift on EVERY scene so nothing is ever fully static.
// A theme = a backdrop palette (base gradient + glow hues) AND a signature ambient `layer`
// that gives it a distinct *character*, not just a recolor: midnight a drifting node graph,
// slate a blueprint grid, dusk floating particles. Content colors (text, cards, good/bad)
// stay shared so legibility is identical across themes. Deterministic, no network, no stock
// imagery, kept well behind content: a *designed* backdrop, not AI-slop filler.
type Layer = "graph" | "grid" | "particles";
export type Theme = {
  bg0: string; bg1: string; focal: string;
  blobs: [string, number, number][];
  layer: Layer; layerColor: string;
};

export const THEMES: Record<string, Theme> = {
  // deep navy, blue/purple aurora + a drifting node graph (network/ML feel)
  midnight: {
    bg0: "#0a0e1f", bg1: "#161d3d", focal: "34%",
    blobs: [["rgba(94,160,255,0.22)", 28, 30], ["rgba(192,132,252,0.18)", 74, 62], ["rgba(74,222,128,0.10)", 52, 90]],
    layer: "graph", layerColor: "150,180,255",
  },
  // cool, neutral/professional + a blueprint grid (systems/infra/security feel)
  slate: {
    bg0: "#0d1117", bg1: "#1f2a3a", focal: "38%",
    blobs: [["rgba(125,211,252,0.20)", 26, 28], ["rgba(148,163,184,0.16)", 72, 60], ["rgba(56,189,248,0.10)", 50, 92]],
    layer: "grid", layerColor: "148,180,210",
  },
  // warm plum -> amber + softly rising particles (vision/generative/editorial feel)
  dusk: {
    bg0: "#140b1e", bg1: "#2a1633", focal: "36%",
    blobs: [["rgba(244,114,182,0.18)", 28, 30], ["rgba(167,139,250,0.18)", 73, 60], ["rgba(251,191,36,0.11)", 52, 90]],
    layer: "particles", layerColor: "251,210,150",
  },
};

// deterministic particle seeds [x%, baseY%, phase] for the dusk layer
const PARTICLES: [number, number, number][] = [
  [10, 80, 0.0], [18, 30, 1.1], [27, 62, 2.3], [35, 14, 3.0], [44, 88, 0.7],
  [52, 40, 1.8], [61, 70, 2.9], [69, 22, 0.4], [77, 56, 1.5], [85, 84, 2.1],
  [90, 36, 3.3], [6, 50, 1.2], [48, 58, 2.6], [33, 46, 0.9], [73, 92, 1.7],
];

/** Active theme + section progress (0..1 across the video) are threaded by PaperVideo. */
export const ThemeCtx = React.createContext<Theme>(THEMES.midnight);
export const ToneCtx = React.createContext<number>(0);

/** midnight — drifting node graph (deterministic sine drift). */
const GraphLayer: React.FC<{ frame: number; color: string; op: number }> = ({ frame, color, op }) => {
  const drift = (i: number, a: number) => Math.sin(frame * 0.012 + i * 1.7 + a * 2.1) * 1.4;
  const pts = NODES.map(([x, y], i) => [x + drift(i, 0), y + drift(i, 1)]);
  return (
    <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"
      style={{ position: "absolute", inset: 0, opacity: op }}>
      {EDGES.map(([a, b], i) => (
        <line key={i} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]}
          stroke={`rgba(${color},0.34)`} strokeWidth={0.12} />
      ))}
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={0.45} fill={`rgba(${color},0.9)`} />
      ))}
    </svg>
  );
};

/** slate — blueprint grid that slowly drifts diagonally (true square cells, in px). */
const GridLayer: React.FC<{ frame: number; color: string; op: number }> = ({ frame, color, op }) => {
  const o = (frame * 0.25) % 88;
  const line = `rgba(${color},0.95)`;
  const mask = "radial-gradient(140% 140% at 50% 45%, #000 60%, transparent 100%)";
  return (
    <AbsoluteFill style={{
      opacity: op,
      backgroundImage:
        `linear-gradient(${line} 2px, transparent 2px), linear-gradient(90deg, ${line} 2px, transparent 2px)`,
      backgroundSize: "88px 88px",
      backgroundPosition: `${o}px ${o}px`,
      maskImage: mask,
      WebkitMaskImage: mask,
    }} />
  );
};

/** dusk — softly rising, twinkling particles (deterministic seeds). */
const ParticleLayer: React.FC<{ frame: number; color: string; op: number }> = ({ frame, color, op }) => (
  <svg width="100%" height="100%" viewBox="0 0 100 100" preserveAspectRatio="none"
    style={{ position: "absolute", inset: 0, opacity: op }}>
    {PARTICLES.map(([x, y, ph], i) => {
      const px = x + Math.sin(frame * 0.006 + ph * 3) * 1.4;
      const py = ((y - frame * 0.02 - ph * 7) % 100 + 100) % 100;  // slow rise + wrap
      const tw = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(frame * 0.035 + ph * 5));
      return <circle key={i} cx={px} cy={py} r={0.5} fill={`rgba(${color},${tw.toFixed(3)})`} />;
    })}
  </svg>
);

/** Ambient backdrop, present on every scene: a themed radial base + slowly drifting glow +
 *  the theme's signature ambient layer + a vignette (reads "intentionally designed", not
 *  black). The glow drifts downward as the video advances (section progress `tone`), so the
 *  backdrop feels authored across the arc without fighting the content. `hero` boosts the
 *  signature layer for the title/outro showcase cards. */
export const Background: React.FC<{ hero?: boolean }> = ({ hero = false }) => {
  const frame = useCurrentFrame();
  const theme = useContext(ThemeCtx);
  const tone = useContext(ToneCtx);
  const op = hero ? 0.62 : 0.3;  // signature layer stays well behind content on body scenes
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(1500px 1000px at 50% ${theme.focal}, ${theme.bg1} 0%, ${theme.bg0} 70%)`,
        overflow: "hidden",
      }}
    >
      {theme.blobs.map(([hue, bx, by], i) => {
        // section progress nudges the glow down the frame (start high, end low) so the
        // backdrop evolves over the video; per-scene drift keeps it alive within a scene.
        const x = bx + Math.sin(frame * 0.008 + i * 2.1) * 6;
        const y = by + (tone - 0.5) * 16 + Math.cos(frame * 0.0065 + i * 1.3) * 5;
        const s = 1 + tone * 0.05 + Math.sin(frame * 0.01 + i) * 0.06;
        return (
          <div key={i} style={{
            position: "absolute", left: `${x}%`, top: `${y}%`, width: 1200, height: 1200,
            transform: `translate(-50%,-50%) scale(${s})`,
            background: `radial-gradient(circle, ${hue} 0%, rgba(0,0,0,0) 60%)`,
            filter: "blur(40px)",
          }} />
        );
      })}
      {theme.layer === "graph" && <GraphLayer frame={frame} color={theme.layerColor} op={op} />}
      {theme.layer === "grid" && <GridLayer frame={frame} color={theme.layerColor} op={op} />}
      {theme.layer === "particles" && <ParticleLayer frame={frame} color={theme.layerColor} op={op} />}
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
