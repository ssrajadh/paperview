/** Default frame rate; a plan may override via meta.fps (ppv render --fps/--draft). */
export const FPS = 30;

/** Cross-fade length between scenes, in frames (~0.4s at 30fps). Each scene is padded
 *  by this much tail so narration ends before the fade — the overlap lands on
 *  silence, so two scenes never talk at once (see PaperVideo / D4a). */
export const TRANSITION = 12;

export const DIMS: Record<string, [number, number]> = {
  "16:9": [1920, 1080],
  "9:16": [1080, 1920],
  "1:1": [1080, 1080],
};

/** Frames of narration for a scene from its measured duration (seconds), at `fps`. */
export const sceneFrames = (s: any, fps: number = FPS): number =>
  Math.max(1, Math.ceil((s.seconds ?? 3) * fps));

/** Visual length of a scene's TransitionSeries.Sequence: narration + fade tail. */
export const sceneVisualFrames = (s: any, fps: number = FPS): number =>
  sceneFrames(s, fps) + TRANSITION;

/** Total timeline length once transitions overlap adjacent scenes by TRANSITION. */
export const totalFrames = (scenes: any[], fps: number = FPS): number => {
  const n = scenes?.length ?? 0;
  if (n === 0) return 1;
  const sum = scenes.reduce((a, s) => a + sceneVisualFrames(s, fps), 0);
  return Math.max(1, sum - (n - 1) * TRANSITION);
};
