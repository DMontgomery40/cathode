import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { bundle } from '@remotion/bundler'
import { renderMedia, selectComposition } from '@remotion/renderer'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const frontendDir = path.resolve(__dirname, '..')
const entryPoint = path.join(frontendDir, 'src', 'remotion', 'index.tsx')
const DEFAULT_APPLE_SILICON_VIDEO_BITRATE = '12M'

export function isVideoToolboxStitchFailure(error) {
  const message = String(error || '')
  return (
    message.includes('h264_videotoolbox')
    || message.includes('hevc_videotoolbox')
    || message.includes('Error setting bitrate property')
    || message.includes('Error while opening encoder')
    || message.includes('Could not open encoder before EOF')
  )
}

export function getRenderAttempts({
  platform = process.platform,
  appleSiliconVideoBitrate = DEFAULT_APPLE_SILICON_VIDEO_BITRATE,
} = {}) {
  if (platform === 'darwin') {
    return [
      {
        label: 'Starting Remotion render',
        detail: `codec=h264 hwaccel=required bitrate=${appleSiliconVideoBitrate}`,
        hardwareAcceleration: 'required',
        videoBitrate: appleSiliconVideoBitrate,
      },
      {
        label: 'Retrying Remotion render',
        detail: 'codec=h264 hwaccel=disable fallback=libx264',
        hardwareAcceleration: 'disable',
        videoBitrate: null,
      },
    ]
  }

  return [
    {
      label: 'Starting Remotion render',
      detail: 'codec=h264 hwaccel=disable',
      hardwareAcceleration: 'disable',
      videoBitrate: null,
    },
  ]
}

async function runRenderAttempt({
  serveUrl,
  composition,
  manifest,
  outputPath,
  attempt,
}) {
  console.log(JSON.stringify({
    type: 'status',
    stage: 'render',
    label: attempt.label,
    detail: attempt.detail,
  }))

  await renderMedia({
    serveUrl,
    composition,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: manifest,
    hardwareAcceleration: attempt.hardwareAcceleration,
    videoBitrate: attempt.videoBitrate,
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
      gl: 'angle',
    },
  })
}

async function main() {
  const [manifestPath, outputPath] = process.argv.slice(2)
  if (!manifestPath || !outputPath) {
    throw new Error('Usage: node render-remotion.mjs <manifest.json> <output.mp4>')
  }

  const manifest = JSON.parse(await fs.readFile(manifestPath, 'utf8'))
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
  const attempts = getRenderAttempts()
  let lastError = null
  for (const [index, attempt] of attempts.entries()) {
    try {
      await runRenderAttempt({
        serveUrl,
        composition,
        manifest,
        outputPath,
        attempt,
      })
      lastError = null
      break
    } catch (error) {
      lastError = error
      if (index === attempts.length - 1 || !isVideoToolboxStitchFailure(error)) {
        throw error
      }

      console.warn(JSON.stringify({
        type: 'status',
        stage: 'render-fallback',
        label: 'VideoToolbox failed, retrying on CPU',
        detail: String(error),
      }))
    }
  }

  if (lastError) {
    throw lastError
  }
  console.log(JSON.stringify({
    type: 'done',
    stage: 'complete',
    label: 'Render complete',
    detail: outputPath,
  }))
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.stack || error.message : String(error))
    process.exit(1)
  })
}
