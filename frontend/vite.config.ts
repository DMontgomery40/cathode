import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

// Remotion is an optional capability. Resolve the live composition player only when the
// optional packages are installed; otherwise alias `remotion-player-surface` to a
// Remotion-free stub so the build never needs @remotion/* and the app degrades to the
// always-available ffmpeg/plain-media playback path.
const require = createRequire(import.meta.url)
const remotionPlayerInstalled = (() => {
  try {
    require.resolve('@remotion/player')
    return true
  } catch {
    return false
  }
})()

const remotionPlayerSurface = fileURLToPath(
  new URL(
    remotionPlayerInstalled
      ? './src/remotion/RemotionPlayerSurface.tsx'
      : './src/remotion/RemotionPlayerSurface.stub.tsx',
    import.meta.url,
  ),
)

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      'remotion-player-surface': remotionPlayerSurface,
    },
  },
  server: {
    host: '127.0.0.1',
    port: Number(process.env.BETTUBE_STUDIO_FRONTEND_PORT || 9322),
    proxy: {
      '/api': {
        target: `http://127.0.0.1:${process.env.BETTUBE_STUDIO_API_PORT || 9321}`,
        changeOrigin: true,
      },
    },
  },
  css: {
    preprocessorOptions: {
      scss: {},
    },
  },
})
