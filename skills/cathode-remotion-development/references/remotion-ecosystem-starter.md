# Remotion Ecosystem Starter

This is a bounded official map for future agents. It is not meant to be a full ecosystem survey.

## Official Starting Points

- Main site / docs hub:
  - <https://www.remotion.dev/>
- Next.js starter landing page:
  - <https://next.remotion.dev/>
- Next.js app-router starter landing page:
  - <https://next-app-dir.remotion.dev/>
- Vercel sandbox starter:
  - <https://template-vercel.remotion.dev/>

## Editor Starter

- The official Remotion homepage currently advertises "Remotion Editor Starter" and describes it as a template for custom video editing applications with React and TypeScript:
  - <https://www.remotion.dev/>
- In Cathode today:
  - not adopted
  - useful as reference only if Cathode ever needs a richer timeline/editor product surface

## Current Cathode Remotion Dependencies

In `frontend/package.json`, Cathode currently uses:

- `remotion`
- `@remotion/player`
- `@remotion/renderer`
- `@remotion/transitions`
- `@remotion/three`
- `@react-three/fiber`
- `@react-three/drei`
- `three`

## Not Currently Adopted In Cathode

- Next.js Remotion starter
  - official and useful for app-level hosting/reference patterns
  - not part of Cathode's current React + FastAPI control room
- Vercel sandbox starter
  - official serverless/rendering reference
  - not part of Cathode's current local-first render path
- Editor Starter
  - official product/editor reference
  - not part of Cathode's current scene inspector + player UI

## Why This File Exists

Future agents should not have to search blindly for "what else does Remotion officially ship?" before making a scoped Cathode decision. Start here, then stop once you have the official reference you actually need.
