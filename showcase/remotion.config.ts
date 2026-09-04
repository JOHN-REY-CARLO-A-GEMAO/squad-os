import {Config} from '@remotion/cli/config';

// Keep rendered artifacts crisp for README-sized playback while staying compact.
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
