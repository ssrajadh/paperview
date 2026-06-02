import React from "react";
import { Composition } from "remotion";
import { PaperVideo } from "./PaperVideo";
import { FPS, DIMS, sceneFrames } from "./layout";
import defaultPlan from "./plan.default.json";

/** The scene plan is passed as input props at render time (`ppv render` -> --props).
 *  calculateMetadata derives dimensions + length from it; the committed default
 *  plan keeps the project openable in `remotion studio` and renderable as a smoke test. */
export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Paper"
      component={PaperVideo}
      fps={FPS}
      width={1920}
      height={1080}
      durationInFrames={300}
      defaultProps={{ plan: defaultPlan as any }}
      calculateMetadata={({ props }) => {
        const plan: any = (props as any).plan ?? defaultPlan;
        const [width, height] = DIMS[plan?.meta?.aspect] ?? DIMS["16:9"];
        const durationInFrames = Math.max(
          1,
          (plan.scenes ?? []).reduce((a: number, s: any) => a + sceneFrames(s), 0)
        );
        return { durationInFrames, width, height, props };
      }}
    />
  );
};
