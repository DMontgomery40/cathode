import { JobCard } from '../jobs/JobCard.tsx'
import { DetailGrid } from '../../components/composed/DetailGrid.tsx'
import { WorkspacePanel } from '../../design-system/recipes'
import { formatImageActionLabel, formatImageActionSummary, formatImageActionTime, imageActionStatusClass } from '../../lib/image-action-history.ts'
import type { Job } from '../../lib/api/jobs.ts'
import type { ImageActionHistoryEntry } from '../../lib/schemas/plan.ts'

interface ImageActivityPanelProps {
  project: string
  entries: ImageActionHistoryEntry[]
  jobs: Job[]
}

function failedCount(entries: ImageActionHistoryEntry[]): number {
  return entries.filter((entry) => entry.status === 'error').length
}

function actionValue(entry: ImageActionHistoryEntry, key: string): string {
  const requestValue = entry.request?.[key]
  const resultValue = entry.result?.[key]
  const value = requestValue ?? resultValue
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  return ''
}

export function ImageActivityPanel({ project, entries, jobs }: ImageActivityPanelProps) {
  const recentEntries = entries.slice(0, 6)
  const recentJobs = jobs.slice(0, 3)

  return (
    <WorkspacePanel
      title="Image activity"
      eyebrow="Logs & history"
      copy="Recent scene image actions and background asset job status for the selected project."
    >
      <div className="flex flex-col gap-[var(--space-4)]">
        <div className="workspace-kpi-grid">
          <div>
            <p className="workspace-eyebrow">Recent actions</p>
            <div className="workspace-panel-title text-[var(--text-2xl)]">{entries.length}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Background jobs</p>
            <div className="workspace-panel-title text-[var(--text-2xl)]">{jobs.length}</div>
          </div>
          <div>
            <p className="workspace-eyebrow">Failures</p>
            <div className="workspace-panel-title text-[var(--text-2xl)]">{failedCount(entries)}</div>
          </div>
        </div>

        <div className="grid gap-[var(--space-4)] xl:grid-cols-[minmax(0,1.25fr)_minmax(18rem,1fr)]">
          <div className="flex flex-col gap-[var(--space-3)]">
            <div className="flex items-center justify-between gap-[var(--space-3)]">
              <div>
                <div className="workspace-eyebrow">Recent scene image actions</div>
                <p className="workspace-panel-copy m-0">Uploads, generations, and edits are saved with the project history.</p>
              </div>
            </div>

            {recentEntries.length === 0 ? (
              <div className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-4)] py-[var(--space-4)] text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
                No image actions recorded yet. Upload, generate, or edit a scene image and the latest action summaries will land here.
              </div>
            ) : (
              recentEntries.map((entry, index) => (
                <details
                  key={`${entry.happened_at ?? 'entry'}-${index}`}
                  className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-4)] py-[var(--space-3)]"
                >
                  <summary className="cursor-pointer list-none">
                    <div className="flex flex-wrap items-start justify-between gap-[var(--space-3)]">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-[var(--space-2)]">
                          <div className="text-[var(--text-primary)]" style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--weight-medium)' }}>
                            {formatImageActionLabel(entry.action)}
                          </div>
                          <span
                            className={`rounded-full border px-[var(--space-2)] py-[2px] font-[family-name:var(--font-mono)] text-[10px] ${imageActionStatusClass(entry.status)}`}
                          >
                            {entry.status || 'unknown'}
                          </span>
                        </div>
                        <div className="mt-[var(--space-1)] text-[var(--text-secondary)]" style={{ fontSize: 'var(--text-sm)' }}>
                          {entry.scene_title || 'Untitled scene'}
                        </div>
                        <div className="mt-[var(--space-1)] text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-xs)' }}>
                          {formatImageActionSummary(entry)}
                        </div>
                      </div>
                      <div className="text-right text-[var(--text-tertiary)]" style={{ fontSize: '10px', fontFamily: 'var(--font-mono)' }}>
                        <div>{formatImageActionTime(entry.happened_at)}</div>
                        <div>Scene {entry.scene_index ?? '--'}</div>
                      </div>
                    </div>
                  </summary>

                  <div className="mt-[var(--space-3)] flex flex-col gap-[var(--space-3)]">
                    <DetailGrid
                      items={[
                        { label: 'Provider', value: actionValue(entry, 'provider') || 'Project default' },
                        { label: 'Model', value: actionValue(entry, 'model') || 'Model default', title: actionValue(entry, 'model') },
                        { label: 'Output', value: actionValue(entry, 'output_path') ? 'Saved' : entry.status || 'Recorded' },
                        { label: 'Scene', value: entry.scene_title || `Scene ${entry.scene_index ?? '--'}` },
                      ]}
                    />
                    {entry.error && (
                      <div className="text-[var(--signal-danger)]" role="alert" style={{ fontSize: 'var(--text-xs)' }}>
                        {entry.error}
                      </div>
                    )}
                  </div>
                </details>
              ))
            )}
          </div>

          <div className="flex flex-col gap-[var(--space-3)]">
            <div className="flex items-end justify-between gap-[var(--space-3)]">
              <div>
                <div className="workspace-eyebrow">Background image jobs</div>
                <p className="workspace-panel-copy m-0">Asset passes keep their step trail here. Expand a job to inspect status and timing.</p>
              </div>
              {project && (
                <a
                  href={`/projects/${project}/queue`}
                  className="rounded-[var(--radius-md)] border border-[var(--border-subtle)] px-[var(--space-3)] py-[var(--space-2)] text-[var(--text-secondary)] no-underline hover:bg-[var(--surface-stage)]"
                  style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--weight-medium)' }}
                >
                  Open Queue
                </a>
              )}
            </div>

            {recentJobs.length === 0 ? (
              <div className="rounded-[var(--radius-lg)] border border-[var(--border-subtle)] bg-[var(--surface-stage)] px-[var(--space-4)] py-[var(--space-4)] text-[var(--text-tertiary)]" style={{ fontSize: 'var(--text-sm)' }}>
                No background asset jobs yet. Generate all assets and the latest job records will show up here.
              </div>
            ) : (
              recentJobs.map((job) => (
                <JobCard key={job.job_id} job={job} project={project} />
              ))
            )}
          </div>
        </div>
      </div>
    </WorkspacePanel>
  )
}
