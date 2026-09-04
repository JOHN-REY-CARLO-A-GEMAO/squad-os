import {Composition} from 'remotion';
import {SquadOSShowcase} from './SquadOSShowcase';

export const VIDEO_FPS = 30;
export const VIDEO_DURATION = VIDEO_FPS * 20;
export const VIDEO_WIDTH = 1280;
export const VIDEO_HEIGHT = 720;

export const RemotionRoot = () => {
  return (
    <Composition
      id="SquadOSShowcase"
      component={SquadOSShowcase}
      durationInFrames={VIDEO_DURATION}
      fps={VIDEO_FPS}
      width={VIDEO_WIDTH}
      height={VIDEO_HEIGHT}
    />
  );
};
