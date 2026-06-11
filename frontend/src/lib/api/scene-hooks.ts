import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest, jsonBody } from './client'
import type { Job, JobLog } from './jobs'
import type { Plan } from '../schemas/plan'

type QueryOpts = { enabled?: boolean; refetchInterval?: number; tailLines?: number }

function projectPlanKey(project: string) {
  return ['project', project, 'plan'] as const
}

function setPlan(queryClient: ReturnType<typeof useQueryClient>, project: string, plan: Plan) {
  queryClient.setQueryData(projectPlanKey(project), plan)
  void queryClient.invalidateQueries({ queryKey: ['projects'] })
}

export function useSavePlan(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['save plan', project],
    mutationFn: (plan: Plan) => apiRequest<Plan>(`/api/projects/${encodeURIComponent(project)}/plan`, {
      method: 'PUT',
      body: jsonBody(plan),
    }),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

function uploadSceneFile(project: string, sceneUid: string, file: File, kind: 'image' | 'video') {
  const body = new FormData()
  body.append('file', file)
  return apiRequest<Plan>(`/api/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/${kind}-upload`, {
    method: 'POST',
    body,
  })
}

export function useUploadSceneImage(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['upload scene image', project],
    mutationFn: ({ sceneUid, file }: { sceneUid: string; file: File }) => uploadSceneFile(project, sceneUid, file, 'image'),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useUploadSceneVideo(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['upload scene video', project],
    mutationFn: ({ sceneUid, file }: { sceneUid: string; file: File }) => uploadSceneFile(project, sceneUid, file, 'video'),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

function scenePost(project: string, sceneUid: string, endpoint: string, body?: unknown) {
  return apiRequest<Plan>(`/api/projects/${encodeURIComponent(project)}/scenes/${encodeURIComponent(sceneUid)}/${endpoint}`, {
    method: 'POST',
    body: body === undefined ? undefined : jsonBody(body),
  })
}

export function useGenerateSceneImage(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['generate scene image', project],
    mutationFn: ({ sceneUid, provider, model }: { sceneUid: string; provider?: string; model?: string }) => scenePost(project, sceneUid, 'image-generate', { provider, model }),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useGenerateSceneVideo(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['generate scene video', project],
    mutationFn: ({ sceneUid, ...body }: { sceneUid: string; provider?: string; model?: string; model_selection_mode?: string; quality_mode?: string; generate_audio?: boolean }) => scenePost(project, sceneUid, 'video-generate', body),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useGenerateSceneAudio(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['generate scene audio', project],
    mutationFn: ({ sceneUid, ...body }: { sceneUid: string; tts_provider?: string; voice?: string; speed?: number }) => scenePost(project, sceneUid, 'audio-generate', body),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useEditSceneImage(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['edit scene image', project],
    mutationFn: ({ sceneUid, feedback, model }: { sceneUid: string; feedback: string; model?: string }) => scenePost(project, sceneUid, 'image-edit', { feedback, model }),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useRefinePrompt(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['refine prompt', project],
    mutationFn: ({ sceneUid, feedback, provider }: { sceneUid: string; feedback: string; provider?: string }) => scenePost(project, sceneUid, 'prompt-refine', { feedback, provider }),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useRefineNarration(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['refine narration', project],
    mutationFn: ({ sceneUid, feedback, provider }: { sceneUid: string; feedback: string; provider?: string }) => scenePost(project, sceneUid, 'narration-refine', { feedback, provider }),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useGenerateScenePreview(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['generate scene preview', project],
    mutationFn: ({ sceneUid }: { sceneUid: string }) => scenePost(project, sceneUid, 'preview'),
    onSuccess: (plan) => setPlan(queryClient, project, plan),
  })
}

export function useGenerateAssets(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['generate assets', project],
    mutationFn: () => apiRequest<Job>(`/api/projects/${encodeURIComponent(project)}/assets`, { method: 'POST' }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useStartRender(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['start render', project],
    mutationFn: (body?: { output_filename?: string; fps?: number }) => apiRequest<Job>(`/api/projects/${encodeURIComponent(project)}/render`, {
      method: 'POST',
      body: jsonBody(body ?? {}),
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useRunAgentDemo(project: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['run agent demo', project],
    mutationFn: (body?: Record<string, unknown>) => apiRequest<Job>(`/api/projects/${encodeURIComponent(project)}/agent-demo`, {
      method: 'POST',
      body: jsonBody(body ?? {}),
    }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['project', project, 'jobs'] })
      void queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })
}

export function useProjectJobs(project: string | null | undefined, options?: QueryOpts) {
  return useQuery({
    queryKey: ['project', project, 'jobs'],
    // 'new' is the unsaved-project route segment, not a real project name.
    enabled: Boolean(project && project !== 'new' && (options?.enabled ?? true)),
    refetchInterval: options?.refetchInterval,
    queryFn: () => apiRequest<Job[]>(`/api/projects/${encodeURIComponent(String(project))}/jobs`),
  })
}

export function useCancelJob() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationKey: ['cancel job'],
    mutationFn: ({ jobId, project }: { jobId: string; project?: string }) => apiRequest<Job>(
      `/api/jobs/${encodeURIComponent(jobId)}/cancel${project ? `?project=${encodeURIComponent(project)}` : ''}`,
      { method: 'POST' },
    ),
    onSuccess: (job) => {
      if (job.project_name) {
        void queryClient.invalidateQueries({ queryKey: ['project', job.project_name, 'jobs'] })
        void queryClient.invalidateQueries({ queryKey: ['projects'] })
      }
    },
  })
}

export function useJobLog(project: string | null | undefined, jobId: string | null | undefined, options?: QueryOpts) {
  const tailLines = options?.tailLines ?? 200
  return useQuery({
    queryKey: ['project', project, 'jobs', jobId, 'log', tailLines],
    enabled: Boolean(project && jobId && (options?.enabled ?? true)),
    refetchInterval: options?.refetchInterval,
    queryFn: () => apiRequest<JobLog>(`/api/projects/${encodeURIComponent(String(project))}/jobs/${encodeURIComponent(String(jobId))}/log?tail_lines=${tailLines}`),
    retry: false,
  })
}

export function useSceneRemotionManifest(project: string | null | undefined, sceneUid: string | null | undefined, options?: QueryOpts) {
  return useQuery({
    queryKey: ['project', project, 'scene', sceneUid, 'remotion-manifest'],
    enabled: Boolean(project && sceneUid && (options?.enabled ?? true)),
    queryFn: () => apiRequest<Record<string, unknown>>(`/api/projects/${encodeURIComponent(String(project))}/scenes/${encodeURIComponent(String(sceneUid))}/remotion-manifest`),
    retry: false,
  })
}
