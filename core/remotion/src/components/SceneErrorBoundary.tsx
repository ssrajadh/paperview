import React from "react";
import { AbsoluteFill } from "remotion";
import { Background, C, FONT } from "../theme";

/** Catches a render error in a single scene so one broken component never aborts the
 *  whole video (D6 graceful degradation). The fallback is deliberately minimal — just
 *  the backdrop + the scene's narration as text — so it cannot itself throw. */
export class SceneErrorBoundary extends React.Component<
  { fallbackText?: string; children: React.ReactNode },
  { failed: boolean }
> {
  constructor(props: { fallbackText?: string; children: React.ReactNode }) {
    super(props);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch(error: unknown) {
    // surfaces in the render log without failing the render
    console.warn("[ppv] scene render failed, using text fallback:", error);
  }
  render() {
    if (!this.state.failed) return this.props.children;
    const text = (this.props.fallbackText || "").trim();
    return (
      <AbsoluteFill style={{ fontFamily: FONT }}>
        <Background />
        <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", padding: 160, textAlign: "center" }}>
          <div style={{ color: C.text, fontSize: 56, fontWeight: 700, lineHeight: 1.25, maxWidth: 1500 }}>
            {text || "—"}
          </div>
        </AbsoluteFill>
      </AbsoluteFill>
    );
  }
}
