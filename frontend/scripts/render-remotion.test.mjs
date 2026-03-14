import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getRenderAttempts,
  isVideoToolboxStitchFailure,
} from './render-remotion.mjs'

test('darwin render attempts prefer VideoToolbox and then fall back to CPU', () => {
  const attempts = getRenderAttempts({ platform: 'darwin', appleSiliconVideoBitrate: '10M' })

  assert.equal(attempts.length, 2)
  assert.deepEqual(attempts[0], {
    label: 'Starting Remotion render',
    detail: 'codec=h264 hwaccel=required bitrate=10M',
    hardwareAcceleration: 'required',
    videoBitrate: '10M',
  })
  assert.deepEqual(attempts[1], {
    label: 'Retrying Remotion render',
    detail: 'codec=h264 hwaccel=disable fallback=libx264',
    hardwareAcceleration: 'disable',
    videoBitrate: null,
  })
})

test('non-darwin render attempts stay CPU-only', () => {
  const attempts = getRenderAttempts({ platform: 'linux' })

  assert.deepEqual(attempts, [
    {
      label: 'Starting Remotion render',
      detail: 'codec=h264 hwaccel=disable',
      hardwareAcceleration: 'disable',
      videoBitrate: null,
    },
  ])
})

test('VideoToolbox failure detector matches encoder bootstrap errors', () => {
  assert.equal(
    isVideoToolboxStitchFailure('[h264_videotoolbox] Error setting bitrate property: -12900'),
    true,
  )
  assert.equal(
    isVideoToolboxStitchFailure('Could not open encoder before EOF'),
    true,
  )
  assert.equal(
    isVideoToolboxStitchFailure('ENOENT: missing manifest file'),
    false,
  )
})
