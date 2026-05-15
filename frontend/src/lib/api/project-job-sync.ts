import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { Job } from './jobs.ts'

const TERMINAL_STATUSES = new Set(['succeeded', 'partial_success', 'failed', 'cancelled', 'error'])

function jobTimestamp(job: Job): number {
  const candidate = job.updated_utc ?? job.created_utc ?? ''
  const value = Date.parse(candidate)
  return Number.isNaN(value) ? 0 : value
}

export function useInvalidateProjectOnJobCompletion(
  project: string,
  jobs: Job[] | undefined,
  stages: string[],
) {
  const queryClient = useQueryClient()
  const lastSignatureRef = useRef<string | null>(null)
  const stagesKey = stages.join('|')

  useEffect(() => {
    if (!project || !jobs?.length || !stagesKey) {
      return
    }

    const watchedStages = new Set(stagesKey.split('|').filter(Boolean))
    const latestRelevantJob = [...jobs]
      .filter((job) => watchedStages.has(String(job.requested_stage || '')) || watchedStages.has(String(job.current_stage || '')))
      .sort((left, right) => jobTimestamp(right) - jobTimestamp(left))[0]

    if (!latestRelevantJob) {
      return
    }

    const signature = [
      latestRelevantJob.job_id,
      latestRelevantJob.status,
      latestRelevantJob.updated_utc ?? latestRelevantJob.created_utc ?? '',
    ].join(':')

    if (lastSignatureRef.current === signature) {
      return
    }
    lastSignatureRef.current = signature

    if (!TERMINAL_STATUSES.has(latestRelevantJob.status)) {
      return
    }

    void queryClient.invalidateQueries({ queryKey: ['plan', project] })
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
  }, [jobs, project, queryClient, stagesKey])
}
