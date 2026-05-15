import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import {
  uploadSceneImage,
  uploadSceneVideo,
  editSceneImage,
  generateSceneImage,
  generateSceneVideo,
  generateSceneAudio,
  refinePrompt,
  refineNarration,
  generateScenePreview,
  fetchSceneRemotionManifest,
} from './scenes.ts'
import { savePlan } from './plans.ts'
import { startRender, generateAssets } from './render.ts'
import { fetchProjectJobs, fetchJobStatus, cancelJob, dispatchAgentDemo } from './jobs.ts'
import { fetchProjectJobLog } from './jobs.ts'
import type { Plan } from '../schemas/plan.ts'

function invalidateRemotionQueries(qc: ReturnType<typeof useQueryClient>, project: string) {
  void qc.invalidateQueries({ queryKey: ['remotion-manifest', project] })
  void qc.invalidateQueries({ queryKey: ['scene-remotion-manifest', project] })
}

export function useSavePlan(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['save plan', project],
    mutationFn: (plan: Plan) => savePlan(project, plan),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useUploadSceneImage(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['upload image', project],
    mutationFn: ({ sceneUid, file }: { sceneUid: string; file: File }) =>
      uploadSceneImage(project, sceneUid, file),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useUploadSceneVideo(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['upload video', project],
    mutationFn: ({ sceneUid, file }: { sceneUid: string; file: File }) =>
      uploadSceneVideo(project, sceneUid, file),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useGenerateSceneImage(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['generate image', project],
    mutationFn: ({ sceneUid, opts }: { sceneUid: string; opts?: { provider?: string; model?: string } }) =>
      generateSceneImage(project, sceneUid, opts),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useGenerateSceneVideo(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['generate video', project],
    mutationFn: ({ sceneUid, opts }: { sceneUid: string; opts?: { provider?: string; model?: string; model_selection_mode?: string; quality_mode?: string; generate_audio?: boolean } }) =>
      generateSceneVideo(project, sceneUid, opts),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useEditSceneImage(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['edit image', project],
    mutationFn: ({ sceneUid, feedback, opts }: { sceneUid: string; feedback: string; opts?: { model?: string } }) =>
      editSceneImage(project, sceneUid, feedback, opts),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useGenerateSceneAudio(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['generate audio', project],
    mutationFn: ({ sceneUid, opts }: { sceneUid: string; opts?: { tts_provider?: string; voice?: string; speed?: number } }) =>
      generateSceneAudio(project, sceneUid, opts),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useRefinePrompt(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['refine prompt', project],
    mutationFn: ({ sceneUid, feedback }: { sceneUid: string; feedback: string }) =>
      refinePrompt(project, sceneUid, feedback),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useRefineNarration(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['refine narration', project],
    mutationFn: ({ sceneUid, feedback }: { sceneUid: string; feedback: string }) =>
      refineNarration(project, sceneUid, feedback),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useGenerateScenePreview(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['generate preview', project],
    mutationFn: (sceneUid: string) => generateScenePreview(project, sceneUid),
    onSuccess: (data: Plan) => {
      qc.setQueryData(['plan', project], data)
      invalidateRemotionQueries(qc, project)
    },
  })
}

export function useSceneRemotionManifest(project: string, sceneUid: string | null, opts?: { enabled?: boolean }) {
  return useQuery({
    queryKey: ['scene-remotion-manifest', project, sceneUid],
    queryFn: () => fetchSceneRemotionManifest(project, sceneUid!),
    enabled: Boolean(project && sceneUid && opts?.enabled !== false),
  })
}

export function useStartRender(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['start render', project],
    mutationFn: (opts?: { output_filename?: string; fps?: number }) =>
      startRender(project, opts),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', project] })
    },
  })
}

export function useGenerateAssets(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['generate assets', project],
    mutationFn: () => generateAssets(project),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', project] })
    },
  })
}

export function useRunAgentDemo(project: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['agent demo', project],
    mutationFn: (request: {
      scene_uids?: string[]
      preferred_agent?: string
      workspace_path?: string
      app_url?: string
      launch_command?: string
      expected_url?: string
      run_until?: string
    }) => dispatchAgentDemo(project, request),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['jobs', project] })
    },
  })
}

export function useProjectJobs(project: string, opts?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: ['jobs', project],
    queryFn: () => fetchProjectJobs(project),
    enabled: !!project && project !== 'new',
    refetchInterval: opts?.refetchInterval ?? false,
  })
}

export function useJobStatus(jobId: string | null, project?: string) {
  return useQuery({
    queryKey: ['job', jobId],
    queryFn: () => fetchJobStatus(jobId!, project),
    enabled: !!jobId,
    refetchInterval: 2000,
  })
}

export function useCancelJob() {
  const qc = useQueryClient()
  return useMutation({
    mutationKey: ['cancel job'],
    mutationFn: ({ jobId, project }: { jobId: string; project?: string }) =>
      cancelJob(jobId, project),
    onSuccess: (_, { project }) => {
      if (project) void qc.invalidateQueries({ queryKey: ['jobs', project] })
    },
  })
}

export function useJobLog(project: string, jobId: string | null, opts?: { enabled?: boolean; tailLines?: number }) {
  return useQuery({
    queryKey: ['job-log', project, jobId, opts?.tailLines ?? 200],
    queryFn: () => fetchProjectJobLog(project, jobId!, opts?.tailLines ?? 200),
    enabled: Boolean(project && jobId && opts?.enabled !== false),
    refetchInterval: opts?.enabled === false ? false : 3000,
  })
}
