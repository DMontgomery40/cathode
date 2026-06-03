export interface AcceptedFileType {
  extension?: string
  mime?: string
}

const IMAGE_TYPES: AcceptedFileType[] = [
  { extension: '.png', mime: 'image/png' },
  { extension: '.jpg', mime: 'image/jpeg' },
  { extension: '.jpeg', mime: 'image/jpeg' },
  { extension: '.webp', mime: 'image/webp' },
]

const VIDEO_TYPES: AcceptedFileType[] = [
  { extension: '.mp4', mime: 'video/mp4' },
  { extension: '.mov', mime: 'video/quicktime' },
  { extension: '.webm', mime: 'video/webm' },
]

export function getAcceptedFileTypes(accept?: string): AcceptedFileType[] | null {
  if (!accept) return null
  if (accept.includes('image/*') && accept.includes('video/*')) return [...IMAGE_TYPES, ...VIDEO_TYPES]
  if (accept.includes('image/*')) return IMAGE_TYPES
  if (accept.includes('video/*')) return VIDEO_TYPES
  return accept.split(',').map((value) => ({ extension: value.trim().toLowerCase() })).filter((item) => item.extension)
}

export function acceptedFileTypesForPicker(accept?: string): string[] {
  if (!accept) return []
  const tokens = accept.split(',').map((value) => value.trim()).filter(Boolean)
  if (tokens.length > 0) return tokens
  const acceptedTypes = getAcceptedFileTypes(accept) ?? []
  return acceptedTypes.flatMap((type) => [type.mime, type.extension].filter(Boolean) as string[])
}

function fileAccepted(file: File, acceptedTypes: AcceptedFileType[] | null): boolean {
  if (!acceptedTypes || acceptedTypes.length === 0) return true
  const name = file.name.toLowerCase()
  const mime = file.type.toLowerCase()
  return acceptedTypes.some((type) => {
    return Boolean((type.mime && mime === type.mime) || (type.extension && name.endsWith(type.extension)))
  })
}

export function splitAcceptedFiles(
  files: File[],
  acceptedOrTypes?: string | AcceptedFileType[] | null,
  options?: { multiple?: boolean },
): { accepted: File[]; rejected: File[] } {
  const acceptedTypes = typeof acceptedOrTypes === 'string' ? getAcceptedFileTypes(acceptedOrTypes) : acceptedOrTypes ?? null
  const accepted: File[] = []
  const rejected: File[] = []
  for (const file of files) {
    if (fileAccepted(file, acceptedTypes) && (options?.multiple !== false || accepted.length === 0)) {
      accepted.push(file)
    } else {
      rejected.push(file)
    }
  }
  return { accepted, rejected }
}

export function describeRejectedFiles(rejected: File[], acceptedTypes?: AcceptedFileType[] | null): string {
  if (!rejected.length) return ''
  const extensions = (acceptedTypes ?? []).map((type) => type.extension).filter(Boolean).join(', ')
  return extensions
    ? `Unsupported file type. Accepted: ${extensions}.`
    : 'Unsupported file type.'
}

export async function filesFromDropItems(
  items: Iterable<{ kind?: string; getFile?: () => Promise<File> }>,
): Promise<File[]> {
  const files: File[] = []
  for (const item of items) {
    if (item.kind && item.kind !== 'file') {
      continue
    }
    const file = await item.getFile?.()
    if (file) {
      files.push(file)
    }
  }
  return files
}

export function uploadRejectionMessage(rejected: File[], accept?: string): string {
  return describeRejectedFiles(rejected, getAcceptedFileTypes(accept))
}
