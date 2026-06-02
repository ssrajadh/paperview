import React from "react";
import { Composition } from "remotion";
import plan from "./plan.json";
import { PaperVideo, FPS, totalFrames } from "./PaperVideo";

const DIMS: Record<string, [number, number]> = {
  "16:9": [1920, 1080],
  "9:16": [1080, 1920],
  "1:1": [1080, 1080],
};

export const RemotionRoot: React.FC = () => {
  const [width, height] = DIMS[(plan as any).meta?.aspect ?? "16:9"] ?? DIMS["16:9"];
  return (
    <Composition
      id="Paper"
      component={PaperVideo}
      durationInFrames={Math.max(1, totalFrames)}
      fps={FPS}
      width={width}
      height={height}
    />
  );
};
