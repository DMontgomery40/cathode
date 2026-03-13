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
  const serveUrl = await bundle({
    entryPoint,
    onProgress: () => undefined,
  })

  const composition = await selectComposition({
    serveUrl,
    id: 'CathodeRender',
    inputProps: manifest,
  })

  await renderMedia({
    serveUrl,
    composition,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: manifest,
    chromiumOptions: {
      disableWebSecurity: true,
    },
  })
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error))
  process.exit(1)
})
