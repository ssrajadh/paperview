import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { REGISTRY } from "./components";
import { sceneFrames } from "./layout";

/** The whole video. `plan` arrives as input props (see Root calculateMetadata);
 *  per-scene narration durations are folded in as `scene.seconds` by `ppv render`. */
export const PaperVideo: React.FC<{ plan: any }> = ({ plan }) => {
  const withAudio = plan?.meta?.audio !== false;
  let from = 0;
  const seqs = (plan?.scenes ?? []).map((s: any) => {
    const dur = sceneFrames(s);
    const Comp = REGISTRY[s.component] ?? REGISTRY["statement"];
    const el = (
      <Sequence key={s.id} from={from} durationInFrames={dur} name={`s${s.id}-${s.component}`}>
        <Comp {...(s.props || {})} />
        {withAudio && <Audio src={staticFile(`audio/scene${s.id}.wav`)} />}
      </Sequence>
    );
    from += dur;
    return el;
  });
  return <AbsoluteFill style={{ backgroundColor: "#0a0e1f" }}>{seqs}</AbsoluteFill>;
};
