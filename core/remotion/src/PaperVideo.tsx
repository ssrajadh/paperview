import React from "react";
import { AbsoluteFill, Audio, staticFile, useVideoConfig } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";
import { REGISTRY } from "./components";
import { SceneErrorBoundary } from "./components/SceneErrorBoundary";
import { sceneVisualFrames, TRANSITION } from "./layout";

/** The whole video. `plan` arrives as input props (see Root calculateMetadata);
 *  per-scene narration durations are folded in as `scene.seconds` by `ppv render`.
 *  Scenes are chained with short cross-fades (no hard cuts). Each scene's visual
 *  length is narration + TRANSITION tail, so the fade overlap lands on silence and
 *  two scenes never narrate at once. Audio isn't opacity-faded, so narration stays
 *  at full volume through the dissolve. */
export const PaperVideo: React.FC<{ plan: any }> = ({ plan }) => {
  const withAudio = plan?.meta?.audio !== false;
  const scenes: any[] = plan?.scenes ?? [];
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0e1f" }}>
      <TransitionSeries>
        {scenes.flatMap((s: any, i: number) => {
          const Comp = REGISTRY[s.component] ?? REGISTRY["statement"];
          const seq = (
            <TransitionSeries.Sequence key={`s${s.id}`} durationInFrames={sceneVisualFrames(s, fps)}>
              <SceneErrorBoundary fallbackText={s.narration}>
                <Comp {...(s.props || {})} />
              </SceneErrorBoundary>
              {withAudio && <Audio src={staticFile(`audio/scene${s.id}.wav`)} />}
            </TransitionSeries.Sequence>
          );
          if (i === scenes.length - 1) return [seq];
          return [
            seq,
            <TransitionSeries.Transition
              key={`t${s.id}`}
              presentation={fade()}
              timing={linearTiming({ durationInFrames: TRANSITION })}
            />,
          ];
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
};
