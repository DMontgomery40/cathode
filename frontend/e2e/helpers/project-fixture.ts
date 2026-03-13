import fs from 'node:fs'
import path from 'node:path'

function repoRoot(): string {
  return path.resolve(process.cwd(), '..')
}

function projectsRoot(): string {
  return path.join(repoRoot(), 'projects')
}

function rewriteProjectReferences(value: unknown, sourceProject: string, targetProject: string): unknown {
  if (typeof value === 'string') {
    return value.replaceAll(sourceProject, targetProject)
  }
  if (Array.isArray(value)) {
    return value.map((item) => rewriteProjectReferences(item, sourceProject, targetProject))
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, inner]) => [key, rewriteProjectReferences(inner, sourceProject, targetProject)]),
    )
  }
  return value
}

export function cloneProjectFixture(sourceProject: string, targetProject: string): void {
  const sourceDir = path.join(projectsRoot(), sourceProject)
  const targetDir = path.join(projectsRoot(), targetProject)

  fs.rmSync(targetDir, { recursive: true, force: true })
  fs.cpSync(sourceDir, targetDir, { recursive: true })

  for (const filename of ['plan.json', 'plan_expanded.json']) {
    const filePath = path.join(targetDir, filename)
    if (!fs.existsSync(filePath)) continue

    const parsed = JSON.parse(fs.readFileSync(filePath, 'utf8'))
    const rewritten = rewriteProjectReferences(parsed, sourceProject, targetProject) as Record<string, unknown>
    fs.writeFileSync(filePath, `${JSON.stringify(rewritten, null, 2)}\n`, 'utf8')
  }
}

export function cleanupProjectFixture(project: string): void {
  fs.rmSync(path.join(projectsRoot(), project), { recursive: true, force: true })
}

export function readProjectPlan(project: string): Record<string, unknown> {
  return JSON.parse(
    fs.readFileSync(path.join(projectsRoot(), project, 'plan.json'), 'utf8'),
  ) as Record<string, unknown>
}
