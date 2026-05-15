const MIME_PREFIX_SEPARATOR = '/'

function normalizeAcceptedTypes(accept?: string | readonly string[]): string[] {
  if (Array.isArray(accept)) {
    return accept
      .map((part) => part.trim().toLowerCase())
      .filter(Boolean)
  }

  const normalizedAccept = typeof accept === 'string' ? accept : ''

  return normalizedAccept
    .split(',')
    .map((part: string) => part.trim().toLowerCase())
    .filter(Boolean)
}

function mimeTypeMatches(mimeType: string, acceptedType: string): boolean {
  if (acceptedType.endsWith('/*')) {
    const [prefix] = acceptedType.split(MIME_PREFIX_SEPARATOR)
    return mimeType.startsWith(`${prefix}/`)
  }

  return mimeType === acceptedType
}

export function fileMatchesAcceptedTypes(file: File, accept?: string | readonly string[]): boolean {
  const acceptedTypes = normalizeAcceptedTypes(accept)
  if (acceptedTypes.length === 0) {
    return true
  }

  const fileMimeType = (file.type || '').toLowerCase()
  const extension = file.name.includes('.') ? `.${file.name.split('.').pop()!.toLowerCase()}` : ''

  return acceptedTypes.some((acceptedType) => (
    acceptedType.startsWith('.')
      ? extension === acceptedType
      : mimeTypeMatches(fileMimeType, acceptedType)
  ))
}

export async function filesFromDropItems(
  items: Iterable<{ kind?: string; getFile?: () => Promise<File> }>,
): Promise<File[]> {
  const resolved: File[] = []

  for (const item of items) {
    if (item?.kind !== 'file' || typeof item.getFile !== 'function') {
      continue
    }
    resolved.push(await item.getFile())
  }

  return resolved
}

export function splitAcceptedFiles(
  files: File[],
  accept?: string | readonly string[],
  options?: { multiple?: boolean },
): { accepted: File[]; rejected: File[] } {
  const accepted: File[] = []
  const rejected: File[] = []
  const allowsMultiple = options?.multiple ?? true

  if (!accept) {
    const normalized = allowsMultiple ? files : files.slice(0, 1)
    return {
      accepted: normalized,
      rejected: allowsMultiple ? [] : files.slice(1),
    }
  }

  for (const file of files) {
    if (fileMatchesAcceptedTypes(file, accept)) {
      accepted.push(file)
    } else {
      rejected.push(file)
    }
  }

  if (!allowsMultiple && accepted.length > 1) {
    rejected.push(...accepted.slice(1))
    accepted.splice(1)
  }

  return { accepted, rejected }
}

export function acceptedFileTypesForPicker(accept?: string | readonly string[]): string[] | undefined {
  const acceptedTypes = normalizeAcceptedTypes(accept)
  return acceptedTypes.length > 0 ? acceptedTypes : undefined
}

export function uploadRejectionMessage(rejected: File[], accept?: string | readonly string[]): string {
  if (rejected.length === 0) {
    return ''
  }

  const names = rejected.map((file) => file.name).join(', ')
  const allowed = normalizeAcceptedTypes(accept).join(', ')
  if (!allowed) {
    return `Could not use: ${names}`
  }

  return `Unsupported file type for ${names}. Allowed: ${allowed}`
}

export const describeRejectedFiles = uploadRejectionMessage
export const getAcceptedFileTypes = acceptedFileTypesForPicker
