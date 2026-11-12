import { describe, expect, it } from 'vitest'
import { UnsupportedBackupFileError, detectBackupKind } from './backup.js'

describe('detectBackupKind', () => {
  it.each([
    ['{"discs": {}}', 'library'],
    ['{"schema_version": 1, "admin": {}}', 'settings'],
    ['{"schema_version": 0}', 'settings'],
    // The settings import accepts a file without schema_version, and explains why it rejects one.
    ['{"admin": {"api": {"port": 8100}}}', 'settings'],
    ['{"name": "x"}', 'settings'],
  ])('detects %s as %s', async (content, kind) => {
    await expect(detectBackupKind(new File([content], 'backup.json'))).resolves.toBe(kind)
  })

  it.each([
    ['not json', 'notes.txt is not a JSON file: choose a library or a settings file.'],
    ['[]', 'notes.txt is neither a library nor a settings file.'],
    ['null', 'notes.txt is neither a library nor a settings file.'],
  ])('rejects %s', async (content, message) => {
    const result = detectBackupKind(new File([content], 'notes.txt'))

    await expect(result).rejects.toThrow(UnsupportedBackupFileError)
    await expect(result).rejects.toThrow(message)
  })
})
