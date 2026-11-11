// The files the Backup section can restore, told apart by their content rather than their name.
export const BACKUP_KINDS = {
  all: { label: 'Full backup', path: '/import/all', replaces: 'library and settings' },
  library: { label: 'Library', path: '/import/library', replaces: 'library' },
  settings: { label: 'Settings', path: '/import/settings', replaces: 'settings' },
}

export const BACKUP_FILE_ACCEPT = '.zip,.json,application/zip,application/json'

// The local file header signature that starts every zip archive ("PK\x03\x04").
const ZIP_SIGNATURE = [0x50, 0x4b, 0x03, 0x04]

export class UnsupportedBackupFileError extends Error {}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

// A zip archive is a full backup, a JSON object with `discs` a library, and any other JSON object goes to
// the settings import, which accepts a file without `schema_version` and explains with its own validation
// why it rejects one. This only routes the file to the right import.
export async function detectBackupKind(file) {
  const signature = new Uint8Array(await file.slice(0, 4).arrayBuffer())
  if (ZIP_SIGNATURE.every((byte, index) => signature[index] === byte)) return 'all'
  let data
  try {
    data = JSON.parse(await file.text())
  } catch {
    throw new UnsupportedBackupFileError(
      `${file.name} is neither a zip archive nor a JSON file: choose a backup, a library or a settings file.`,
    )
  }
  if (!isObject(data)) {
    throw new UnsupportedBackupFileError(`${file.name} is neither a backup, a library nor a settings file.`)
  }
  return 'discs' in data ? 'library' : 'settings'
}
