# SquadOS Remotion showcase

This directory contains the code-driven product tour linked at the top of the repository README. It is a **20-second, 1280×720 Remotion composition** that introduces the real SquadOS workflow:

1. A goal becomes a dependency-aware mission plan.
2. Specialists execute ready DAG tasks in parallel waves.
3. Sandboxed/destructive work pauses for human review and verification.
4. Teams can package reusable workflows as `.sqad` bundles for the Agent Store.

The animation is deliberately made from React, SVG, and CSS only—there are no screenshots, credentials, or runtime data baked into the video.

## Run it locally

```bash
cd showcase
npm install
npm run dev
```

Open the Remotion Studio composition named **`SquadOSShowcase`** to scrub, preview, or change the story.

## Render the README assets

```bash
cd showcase
npm run render  # writes ../assets/squados-showcase.mp4
npm run still   # writes ../assets/squados-showcase-cover.png
```

The default render command creates the MP4 viewers open from the root `README.md`. The still command creates its clickable cover image.

## Project map

- `src/Root.tsx` — composition settings (20 seconds, 30fps, 1280×720)
- `src/SquadOSShowcase.tsx` — storyboard, reusable visual components, and animation timing
- `remotion.config.ts` — rendering defaults

## Update guidance

When a product claim or visual needs to change, update the matching scene in `src/SquadOSShowcase.tsx`, run `npm run check`, then rerun both output commands above. Keep README-facing facts aligned with the root [`README.md`](../README.md) and implementation details in [`AI_CONTEXT.md`](../AI_CONTEXT.md).
