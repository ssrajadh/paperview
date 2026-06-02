import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import plan from "./plan.json";
import durations from "./durations.json";
import { REGISTRY } from "./components";

export const FPS = 30;

const durMap: Record<number, number> = Object.fromEntries(
  (durations as any[]).map((d) => [d.id, d.duration])
);
const frames = (id: number) => Math.max(1, Math.ceil((durMap[id] ?? 3) * FPS));

export const totalFrames = (plan as any).scenes.reduce(
  (acc: number, s: any) => acc + frames(s.id),
  0
);

export const PaperVideo: React.FC = () => {
  const withAudio = (plan as any).meta?.audio !== false;
  let from = 0;
  const seqs = (plan as any).scenes.map((s: any) => {
    const dur = frames(s.id);
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
