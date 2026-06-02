export const FPS = 30;

export const DIMS: Record<string, [number, number]> = {
  "16:9": [1920, 1080],
  "9:16": [1080, 1920],
  "1:1": [1080, 1080],
};

/** Frames for a scene from its measured narration duration (seconds). */
export const sceneFrames = (s: any): number =>
  Math.max(1, Math.ceil((s.seconds ?? 3) * FPS));
