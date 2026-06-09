import type { Scene } from './schemas/plan'
import { projectMediaUrl } from './media-url'

function pathExists(scene: Scene, pathKey: keyof Scene, existsKey: keyof Scene): boolean {
  const pathValue = scene[pathKey]
  if (typeof scene[existsKey] === 'boolean') {
    return Boolean(scene[existsKey])
  }
  return typeof pathValue === 'string' && pathValue.trim().length > 0
}

export function sceneHasRenderableVisual(_project: string, scene: Scene, renderBackend: string | null | undefined = 'ffmpeg'): boolean {
  if (String(scene.scene_type) === 'motion') {
    const motion = scene.motion ?? {}
    const composition = scene.composition ?? {}
    if (renderBackend === 'remotion') return true
    return Boolean(motion.render_path || motion.preview_path || composition.render_path || composition.preview_path || scene.preview_path)
  }
  if (String(scene.scene_type) === 'video') {
    return pathExists(scene, 'video_path', 'video_exists')
  }
  return pathExists(scene, 'image_path', 'image_exists')
}

export function sceneHasRenderableAudio(_project: string, scene: Scene): boolean {
  if (String(scene.scene_type) === 'video' && String(scene.video_audio_source || '') === 'clip') {
    return pathExists(scene, 'video_path', 'video_exists')
  }
  return pathExists(scene, 'audio_path', 'audio_exists')
}

export function sceneHasPreview(_project: string, scene: Scene): boolean {
  return pathExists(scene, 'preview_path', 'preview_exists')
}

export function sceneVisualUrl(project: string, scene: Scene): string | null {
  if (String(scene.scene_type) === 'motion') {
    const motion = scene.motion ?? {}
    const composition = scene.composition ?? {}
    return projectMediaUrl(project, motion.preview_path)
      ?? projectMediaUrl(project, motion.render_path)
      ?? projectMediaUrl(project, composition.preview_path)
      ?? projectMediaUrl(project, composition.render_path)
      ?? projectMediaUrl(project, scene.preview_path)
      ?? projectMediaUrl(project, scene.image_path)
  }
  if (String(scene.scene_type) === 'video') {
    return projectMediaUrl(project, scene.video_path)
  }
  return projectMediaUrl(project, scene.image_path)
}

export function scenePreviewUrl(project: string, scene: Scene): string | null {
  return projectMediaUrl(project, scene.preview_path)
}
