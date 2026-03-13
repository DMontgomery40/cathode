import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { bundle } from '@remotion/bundler'
import { renderMedia, selectComposition } from '@remotion/renderer'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const frontendDir = path.resolve(__dirname, '..')
const entryPoint = path.join(frontendDir, 'src', 'remotion', 'index.tsx')

async function main() {
  const [manifestPath, outputPath] = process.argv.slice(2)
  if (!manifestPath || !outputPath) {
    throw new Error('Usage: node render-remotion.mjs <manifest.json> <output.mp4>')
  }

  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'))
  const hardwareAcceleration = process.platform === 'darwin' ? 'required' : 'disable'
  console.log(JSON.stringify({
    type: 'status',
    stage: 'bundle',
    label: 'Bundling Remotion composition',
    detail: `${manifest.scenes?.length ?? 0} scene(s)`,
  }))
  const serveUrl = await bundle({
    entryPoint,
    onProgress: () => undefined,
  })
  console.log(JSON.stringify({
    type: 'status',
    stage: 'select-composition',
    label: 'Resolving Remotion composition',
    detail: 'Preparing render metadata',
  }))

  const composition = await selectComposition({
    serveUrl,
    id: 'CathodeRender',
    inputProps: manifest,
  })
  console.log(JSON.stringify({
    type: 'status',
    stage: 'render',
    label: 'Starting Remotion render',
    detail: `codec=h264 hwaccel=${hardwareAcceleration}`,
  }))

  await renderMedia({
    serveUrl,
    composition,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: manifest,
    hardwareAcceleration,
    logLevel: 'verbose',
    onProgress: (progress) => {
      console.log(JSON.stringify({
        type: 'progress',
        stage: progress.stitchStage,
        renderedFrames: progress.renderedFrames,
        encodedFrames: progress.encodedFrames,
        renderedDoneIn: progress.renderedDoneIn,
        encodedDoneIn: progress.encodedDoneIn,
        renderEstimatedTime: progress.renderEstimatedTime,
        progress: progress.progress,
      }))
    },
    chromiumOptions: {
      disableWebSecurity: true,
    },
  })
  console.log(JSON.stringify({
    type: 'done',
    stage: 'complete',
    label: 'Render complete',
    detail: outputPath,
  }))
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error))
  process.exit(1)
})
