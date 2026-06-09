import { useQuery } from '@tanstack/react-query'
import { apiRequest } from './client.ts'
import { useProjects } from './hooks.ts'
import type { Job } from './jobs.ts'

export const ACTIVE_JOB_STATUSES = new Set<Job['status']>(['queued', 'running'])

export function isActiveJob(job: Pick<Job, 'status'>): boolean {
  return ACTIVE_JOB_STATUSES.has(job.status)
}

function jobTime(job: Job): number {
  const value = Date.parse(job.updated_utc || job.created_utc || '')
  return Number.isFinite(value) ? value : 0
}

export function useGlobalQueueSummary() {
  const { data: projects, isLoading: projectsLoading } = useProjects()
  const { data: globalJobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['global', 'jobs'],
    queryFn: () => apiRequest<Job[]>('/api/jobs'),
    refetchInterval: 3000,
  })

  const allJobs = [...(globalJobs ?? [])].sort((left, right) => jobTime(right) - jobTime(left))
  const projectNames = Array.from(new Set([
    ...(projects ?? []).map((project) => project.name),
    ...allJobs.map((job) => job.project_name).filter(Boolean),
  ]))


  return {
    projectNames,
    allJobs,
    jobsLoading: projectsLoading || jobsLoading,
    totalCount: allJobs.length,
    activeCount: allJobs.filter(isActiveJob).length,
    queuedCount: allJobs.filter((job) => job.status === 'queued').length,
    runningCount: allJobs.filter((job) => job.status === 'running').length,
    completedCount: allJobs.filter((job) => job.status === 'succeeded').length,
    partialCount: allJobs.filter((job) => job.status === 'partial_success').length,
    failedCount: allJobs.filter((job) => job.status === 'failed').length,
    cancelledCount: allJobs.filter((job) => job.status === 'cancelled').length,
  }
}
