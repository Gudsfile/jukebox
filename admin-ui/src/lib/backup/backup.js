// The files the Backup section can restore, told apart by their content rather than their name.
export const BACKUP_KINDS = {
  library: { label: 'Library', path: '/import/library', replaces: 'library' },
  settings: { label: 'Settings', path: '/import/settings', replaces: 'settings' },
}

export const BACKUP_FILE_ACCEPT = '.json,application/json'

export class UnsupportedBackupFileError extends Error {}

function isObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

// A JSON object with `discs` is a library, any other JSON object goes to the settings import, which
// accepts a file without `schema_version` and explains with its own validation why it rejects one.
// This only routes the file to the right import.
export async function detectBackupKind(file) {
  let data
  try {
    data = JSON.parse(await file.text())
  } catch {
    throw new UnsupportedBackupFileError(`${file.name} is not a JSON file: choose a library or a settings file.`)
  }
  if (!isObject(data)) throw new UnsupportedBackupFileError(`${file.name} is neither a library nor a settings file.`)
  return 'discs' in data ? 'library' : 'settings'
}
