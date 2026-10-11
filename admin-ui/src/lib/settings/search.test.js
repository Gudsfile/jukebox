import { describe, expect, it } from 'vitest'
import { searchSettings } from './search.js'

const settings = [
  {
    path: 'paths.library_path',
    label: 'Library Path',
    default_value: '/default/library.json',
    persisted_value: '/ignored/when/not/persisted.json',
    effective_value: '/default/library.json',
    provenance: 'default',
    is_persisted: false,
  },
  {
    path: 'admin.api.port',
    label: 'Admin API Port',
    default_value: 8000,
    persisted_value: 9000,
    effective_value: 9000,
    provenance: 'file',
    is_persisted: true,
  },
  {
    path: 'jukebox.player.sonos.selected_group',
    label: 'Sélection Sonos',
    default_value: null,
    persisted_value: { coordinator_uid: 'RINCON_1' },
    effective_value: { coordinator_uid: 'RINCON_1' },
    provenance: 'runtime',
    is_persisted: true,
  },
]

const paths = (result) => result.map((setting) => setting.path)

describe('searchSettings', () => {
  it('returns every setting for an empty or blank query', () => {
    expect(searchSettings(settings, '')).toEqual(settings)
    expect(searchSettings(settings, '   ')).toEqual(settings)
    expect(searchSettings(settings, undefined)).toEqual(settings)
  })

  it('matches the label and the path', () => {
    expect(paths(searchSettings(settings, 'library'))).toEqual(['paths.library_path'])
    expect(paths(searchSettings(settings, 'admin.api'))).toEqual(['admin.api.port'])
  })

  it('is case- and accent-insensitive', () => {
    expect(paths(searchSettings(settings, 'SELECTION'))).toEqual(['jukebox.player.sonos.selected_group'])
  })

  it('matches the default, persisted and effective values as displayed', () => {
    expect(paths(searchSettings(settings, '8000'))).toEqual(['admin.api.port'])
    expect(paths(searchSettings(settings, '9000'))).toEqual(['admin.api.port'])
    expect(paths(searchSettings(settings, 'rincon_1'))).toEqual(['jukebox.player.sonos.selected_group'])
    expect(paths(searchSettings(settings, '"coordinator_uid"'))).toEqual(['jukebox.player.sonos.selected_group'])
  })

  it('matches null default values the way they are displayed', () => {
    expect(paths(searchSettings(settings, 'null'))).toEqual(['jukebox.player.sonos.selected_group'])
  })

  it('ignores the persisted value of a non-persisted setting', () => {
    expect(searchSettings(settings, 'ignored')).toEqual([])
  })

  it('matches the provenance', () => {
    expect(paths(searchSettings(settings, 'runtime'))).toEqual(['jukebox.player.sonos.selected_group'])
  })

  it('requires every term to match', () => {
    expect(paths(searchSettings(settings, 'port file'))).toEqual(['admin.api.port'])
    expect(searchSettings(settings, 'port runtime')).toEqual([])
  })
})
