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

  it('detects a zip archive as a full backup', async () => {
    const zip = new File([new Uint8Array([0x50, 0x4b, 0x03, 0x04, 0x14, 0x00])], 'jukebox-backup.zip')

    await expect(detectBackupKind(zip)).resolves.toBe('all')
  })

  it.each([
    ['not json', 'notes.txt is neither a zip archive nor a JSON file: choose a backup, a library or a settings file.'],
    ['[]', 'notes.txt is neither a backup, a library nor a settings file.'],
    ['null', 'notes.txt is neither a backup, a library nor a settings file.'],
    ['PK', 'notes.txt is neither a zip archive nor a JSON file: choose a backup, a library or a settings file.'],
  ])('rejects %s', async (content, message) => {
    const result = detectBackupKind(new File([content], 'notes.txt'))

    await expect(result).rejects.toThrow(UnsupportedBackupFileError)
    await expect(result).rejects.toThrow(message)
  })
})
