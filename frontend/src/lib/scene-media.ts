import type { Scene } from './schemas/plan.ts'
import { hasProjectMediaPath, projectMediaUrl } from './media-url.ts'

function readyHint(exists: boolean | null | undefined, fallback: boolean): boolean {
  return typeof exists === 'boolean' ? exists : fallback
}

function availableMediaUrl(
  project: string,
  rawPath: string | null | undefined,
  exists: boolean | null | undefined,
): string | null {
  if (exists === false) {
    return null
  }
  return projectMediaUrl(project, rawPath)
}

export function scenePreviewUrl(project: string, scene: Scene | null | undefined): string | null {
  if (!scene) {
    return null
  }
  return (
    availableMediaUrl(project, scene.composition?.preview_path, scene.composition?.preview_exists)
    || availableMediaUrl(project, scene.composition?.render_path, scene.composition?.render_exists)
    || availableMediaUrl(project, scene.motion?.preview_path, scene.motion?.preview_exists)
    || availableMediaUrl(project, scene.preview_path, scene.preview_exists)
    || availableMediaUrl(project, scene.motion?.render_path, scene.motion?.render_exists)
  )
}

export function sceneVisualUrl(project: string, scene: Scene | null | undefined): string | null {
  if (!scene) {
    return null
  }
  return (
    availableMediaUrl(project, scene.image_path, scene.image_exists)
    || availableMediaUrl(project, scene.video_path, scene.video_exists)
    || scenePreviewUrl(project, scene)
  )
}

export function sceneHasPreview(project: string, scene: Scene | null | undefined): boolean {
  if (!scene) {
    return false
  }
  return (
    readyHint(scene.composition?.preview_exists, hasProjectMediaPath(project, scene.composition?.preview_path))
    || readyHint(scene.composition?.render_exists, hasProjectMediaPath(project, scene.composition?.render_path))
    || readyHint(scene.motion?.preview_exists, hasProjectMediaPath(project, scene.motion?.preview_path))
    || readyHint(scene.preview_exists, hasProjectMediaPath(project, scene.preview_path))
    || readyHint(scene.motion?.render_exists, hasProjectMediaPath(project, scene.motion?.render_path))
  )
}

export function sceneHasRenderableVisual(
  project: string,
  scene: Scene | null | undefined,
  renderBackend: string | null | undefined,
): boolean {
  if (!scene) {
    return false
  }

  const sceneType = String(scene.scene_type || 'image')
  const compositionMode = String(scene.composition?.mode || '')
  if (sceneType === 'video') {
    return readyHint(scene.video_exists, hasProjectMediaPath(project, scene.video_path))
  }
  if (sceneType === 'motion' || (renderBackend === 'remotion' && compositionMode === 'native')) {
    if (renderBackend === 'remotion') {
      return Boolean(
        String(scene.composition?.family || scene.motion?.template_id || '').trim(),
      )
    }
    return (
      readyHint(scene.composition?.render_exists, hasProjectMediaPath(project, scene.composition?.render_path))
      || readyHint(scene.composition?.preview_exists, hasProjectMediaPath(project, scene.composition?.preview_path))
      || readyHint(scene.motion?.render_exists, hasProjectMediaPath(project, scene.motion?.render_path))
      || readyHint(scene.motion?.preview_exists, hasProjectMediaPath(project, scene.motion?.preview_path))
      || readyHint(scene.preview_exists, hasProjectMediaPath(project, scene.preview_path))
    )
  }
  return readyHint(scene.image_exists, hasProjectMediaPath(project, scene.image_path))
}

export function sceneHasRenderableAudio(
  project: string,
  scene: Scene | null | undefined,
): boolean {
  if (!scene) {
    return false
  }

  const sceneType = String(scene.scene_type || 'image')
  const videoAudioSource = String(scene.video_audio_source || 'narration')
  if (sceneType === 'video' && videoAudioSource === 'clip') {
    return readyHint(scene.video_audio_exists, readyHint(scene.video_exists, hasProjectMediaPath(project, scene.video_path)))
  }

  return readyHint(scene.audio_exists, hasProjectMediaPath(project, scene.audio_path))
}
