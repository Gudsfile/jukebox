import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings.svelte'
import { apiDownload, apiGet, apiPatch, apiPost, apiUpload } from '../api.js'
import { toastStore } from '../stores/toastStore.js'

vi.mock('../api.js', () => ({
  apiDownload: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  apiUpload: vi.fn(),
}))

const displaysResponse = {
  settings: [
    {
      path: 'paths.library_path',
      label: 'Library Path',
      description: 'Location of the shared library JSON file.',
      field_type: 'string',
      section: 'paths',
      section_label: 'Paths',
      choices: [],
      default_value: '/default/library.json',
      persisted_value: null,
      effective_value: '/default/library.json',
      provenance: 'default',
      is_persisted: false,
      is_pinned_default: false,
      requires_restart: false,
      advanced: false,
    },
    {
      path: 'admin.api.port',
      label: 'Admin API Port',
      description: 'TCP port used by the admin API server.',
      field_type: 'integer',
      section: 'admin',
      section_label: 'Admin',
      choices: [],
      default_value: 8000,
      persisted_value: 9000,
      effective_value: 9000,
      provenance: 'file',
      is_persisted: true,
      is_pinned_default: false,
      requires_restart: true,
      advanced: false,
    },
    {
      path: 'jukebox.player.type',
      label: 'Player Type',
      description: 'Playback backend used by jukebox playback.',
      field_type: 'string',
      section: 'player',
      section_label: 'Player',
      choices: [],
      default_value: 'sonos',
      persisted_value: 'sonos',
      effective_value: 'sonos',
      provenance: 'env',
      is_persisted: true,
      is_pinned_default: true,
      requires_restart: true,
      advanced: true,
    },
    {
      path: 'jukebox.player.sonos.selected_group',
      label: 'Sonos Selected Group',
      description: 'The Sonos speaker group used for playback.',
      field_type: 'object',
      section: 'player',
      section_label: 'Player',
      choices: [],
      default_value: null,
      persisted_value: { coordinator_uid: 'RINCON_1', members: [{ uid: 'RINCON_1' }] },
      effective_value: { coordinator_uid: 'RINCON_1', members: [{ uid: 'RINCON_1' }] },
      provenance: 'runtime',
      is_persisted: true,
      is_pinned_default: false,
      requires_restart: false,
      advanced: false,
    },
  ],
  effective_settings_error: null,
}

beforeEach(() => {
  apiDownload.mockReset()
  apiGet.mockReset()
  apiPatch.mockReset()
  apiPost.mockReset()
})

describe('Settings — list', () => {
  it('groups settings by section and shows the effective value + source', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    expect(await screen.findByRole('heading', { name: 'Paths' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Admin' })).toBeInTheDocument()
    expect(screen.getByText('Library Path')).toBeInTheDocument()
    expect(screen.getAllByText('9000')).toHaveLength(2)
    expect(screen.getByText('Settings file')).toBeInTheDocument()
  })

  it('shows the default and persisted values for a persisted override', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Admin API Port')).closest('tr')
    const cells = row.querySelectorAll('td')
    expect(cells[1]).toHaveTextContent('8000')
    expect(cells[2]).toHaveTextContent('9000')
  })

  it('shows the default value and a placeholder for a non-persisted setting', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Library Path')).closest('tr')
    const cells = row.querySelectorAll('td')
    expect(cells[1]).toHaveTextContent('/default/library.json')
    expect(cells[2]).toHaveTextContent('—')
  })

  it('shows the effective-settings-error banner while still listing persisted values', async () => {
    apiGet.mockResolvedValue({ ...displaysResponse, effective_settings_error: 'Settings file is corrupted.' })
    render(Settings, { props: {} })

    expect(await screen.findByText(/Settings file is corrupted\./)).toBeInTheDocument()
    expect(screen.getByText('Admin API Port')).toBeInTheDocument()
  })

  it('shows the error message when loading fails entirely', async () => {
    apiGet.mockRejectedValue(new Error('Network error'))
    render(Settings, { props: {} })

    expect(await screen.findByText('Network error')).toBeInTheDocument()
  })
})

describe('Settings — badges', () => {
  it('shows no badges for a setting that is neither persisted, pinned, restart-required nor advanced', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Library Path')).closest('tr')
    expect(within(row).queryByText('Configured')).not.toBeInTheDocument()
    expect(within(row).queryByText('Pinned default')).not.toBeInTheDocument()
    expect(within(row).queryByText('Restart required')).not.toBeInTheDocument()
    expect(within(row).queryByText('Advanced')).not.toBeInTheDocument()
  })

  it('shows Configured and Restart required badges for a persisted setting that requires a restart', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Admin API Port')).closest('tr')
    expect(within(row).getByText('Configured')).toBeInTheDocument()
    expect(within(row).getByText('Restart required')).toBeInTheDocument()
    expect(within(row).queryByText('Pinned default')).not.toBeInTheDocument()
    expect(within(row).queryByText('Advanced')).not.toBeInTheDocument()
  })

  it('shows all badges for a setting persisted at its pinned default value, requiring restart and advanced', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Player Type')).closest('tr')
    expect(within(row).getByText('Configured')).toBeInTheDocument()
    expect(within(row).getByText('Pinned default')).toBeInTheDocument()
    expect(within(row).getByText('Restart required')).toBeInTheDocument()
    expect(within(row).getByText('Advanced')).toBeInTheDocument()
  })
})

describe('Settings — edit flow', () => {
  it('opens SettingForm for the clicked row and returns to the list on save', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })
    await screen.findByText('Admin API Port')

    const row = screen.getByText('Admin API Port').closest('tr')
    await fireEvent.click(row.querySelector('button'))

    expect(screen.getByRole('heading', { name: 'Edit Admin API Port' })).toBeInTheDocument()
    expect(screen.getByRole('spinbutton')).toHaveValue(9000)
  })

  it('keeps the effective-settings-error banner visible while editing', async () => {
    apiGet.mockResolvedValue({ ...displaysResponse, effective_settings_error: 'Settings file is corrupted.' })
    render(Settings, { props: {} })
    await screen.findByText('Admin API Port')

    const row = screen.getByText('Admin API Port').closest('tr')
    await fireEvent.click(row.querySelector('button'))

    expect(screen.getByRole('heading', { name: 'Edit Admin API Port' })).toBeInTheDocument()
    expect(screen.getByText(/Settings file is corrupted\./)).toBeInTheDocument()
  })
})

describe('Settings — Sonos selected group row', () => {
  it('shows a Manage Speakers button instead of Edit for the Sonos selected group row', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Sonos Selected Group')).closest('tr')
    expect(within(row).getByRole('button', { name: 'Manage Speakers 🔊' })).toBeInTheDocument()
    expect(within(row).queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
  })

  it('calls onManageSpeakers when the Manage Speakers button is clicked', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    const onManageSpeakers = vi.fn()
    render(Settings, { props: { onManageSpeakers } })

    const row = (await screen.findByText('Sonos Selected Group')).closest('tr')
    await fireEvent.click(within(row).getByRole('button', { name: 'Manage Speakers 🔊' }))

    expect(onManageSpeakers).toHaveBeenCalledOnce()
  })

  it('still shows the normal Edit button for other rows', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Admin API Port')).closest('tr')
    expect(within(row).getByRole('button', { name: 'Edit' })).toBeInTheDocument()
  })
})

describe('Settings — search', () => {
  it('shows every setting when the query is empty', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    expect(await screen.findByRole('searchbox', { name: 'Search settings' })).toHaveValue('')
    expect(screen.getAllByRole('table')).toHaveLength(3)
    expect(screen.getByText('Library Path')).toBeInTheDocument()
    expect(screen.getByText('Sonos Selected Group')).toBeInTheDocument()
  })

  it('filters rows live and hides sections with no matching setting', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    await fireEvent.input(await screen.findByRole('searchbox', { name: 'Search settings' }), {
      target: { value: 'PLAYER' },
    })

    expect(screen.getByRole('heading', { name: 'Player' })).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Paths' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Admin' })).not.toBeInTheDocument()
    expect(screen.getByText('Player Type')).toBeInTheDocument()
    expect(screen.getByText('Sonos Selected Group')).toBeInTheDocument()
  })

  it('keeps the section heading above a single matching row', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    await fireEvent.input(await screen.findByRole('searchbox', { name: 'Search settings' }), {
      target: { value: 'env' },
    })

    expect(screen.getByRole('heading', { name: 'Player' })).toBeInTheDocument()
    expect(screen.getByText('Player Type')).toBeInTheDocument()
    expect(screen.queryByText('Sonos Selected Group')).not.toBeInTheDocument()
  })

  it('shows an empty-state message when nothing matches', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    await fireEvent.input(await screen.findByRole('searchbox', { name: 'Search settings' }), {
      target: { value: 'nothing here' },
    })

    expect(screen.getByText('No setting matches “nothing here”')).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
  })

  it('keeps the query after opening and closing the edit form', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    await fireEvent.input(await screen.findByRole('searchbox', { name: 'Search settings' }), {
      target: { value: 'port' },
    })
    await fireEvent.click(
      within(screen.getByText('Admin API Port').closest('tr')).getByRole('button', { name: 'Edit' }),
    )
    expect(screen.queryByRole('searchbox', { name: 'Search settings' })).not.toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.getByRole('searchbox', { name: 'Search settings' })).toHaveValue('port')
    expect(screen.getByText('Admin API Port')).toBeInTheDocument()
    expect(screen.queryByText('Library Path')).not.toBeInTheDocument()
  })

  it.each([
    ['Save', () => apiPatch.mockResolvedValue({})],
    ['Reset', () => apiPost.mockResolvedValue({})],
  ])('keeps the query and the filtering after the list reloads on %s', async (button, mockSubmit) => {
    apiGet.mockResolvedValue(displaysResponse)
    mockSubmit()
    render(Settings, { props: {} })

    await fireEvent.input(await screen.findByRole('searchbox', { name: 'Search settings' }), {
      target: { value: 'port' },
    })
    await fireEvent.click(
      within(screen.getByText('Admin API Port').closest('tr')).getByRole('button', { name: 'Edit' }),
    )
    await fireEvent.click(screen.getByRole('button', { name: button }))

    expect(await screen.findByRole('searchbox', { name: 'Search settings' })).toHaveValue('port')
    expect(apiGet).toHaveBeenCalledTimes(2)
    expect(screen.getByText('Admin API Port')).toBeInTheDocument()
    expect(screen.queryByText('Library Path')).not.toBeInTheDocument()
  })

  it('keeps the Manage Speakers button on a matching Sonos selected group row', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    await fireEvent.input(await screen.findByRole('searchbox', { name: 'Search settings' }), {
      target: { value: 'rincon' },
    })

    const row = screen.getByText('Sonos Selected Group').closest('tr')
    expect(within(row).getByRole('button', { name: 'Manage Speakers 🔊' })).toBeInTheDocument()
    expect(screen.getAllByRole('row')).toHaveLength(2)
  })
})

describe('Settings — PN532 board profile row', () => {
  const pn532Response = {
    settings: [
      {
        path: 'jukebox.reader.pn532.board_profile',
        label: 'PN532 Board Profile',
        description: 'Known board preset. Provides default GPIO pins for the selected module.',
        field_type: 'string',
        section: 'reader',
        section_label: 'Reader',
        choices: [
          { value: 'waveshare_hat', label: 'WaveShare PN532 NFC HAT' },
          { value: 'hiletgo_v3', label: 'HiLetgo PN532 V3' },
          { value: 'custom', label: 'Custom' },
        ],
        default_value: 'waveshare_hat',
        persisted_value: null,
        effective_value: 'waveshare_hat',
        provenance: 'default',
        is_persisted: false,
        is_pinned_default: false,
        requires_restart: true,
        advanced: false,
      },
    ],
    effective_settings_error: null,
  }

  it('shows a Configure PN532 button instead of Edit for the board profile row', async () => {
    apiGet.mockResolvedValue(pn532Response)
    render(Settings, { props: {} })

    const row = (await screen.findByText('PN532 Board Profile')).closest('tr')
    expect(within(row).getByRole('button', { name: 'Configure PN532 🔌' })).toBeInTheDocument()
    expect(within(row).queryByRole('button', { name: 'Edit' })).not.toBeInTheDocument()
  })

  it('calls onConfigurePn532 when the Configure PN532 button is clicked', async () => {
    apiGet.mockResolvedValue(pn532Response)
    const onConfigurePn532 = vi.fn()
    render(Settings, { props: { onConfigurePn532 } })

    const row = (await screen.findByText('PN532 Board Profile')).closest('tr')
    await fireEvent.click(within(row).getByRole('button', { name: 'Configure PN532 🔌' }))

    expect(onConfigurePn532).toHaveBeenCalledOnce()
  })
})

describe('Settings — backup', () => {
  async function openMoreExports() {
    await fireEvent.click(await screen.findByRole('button', { name: 'More export options' }))
  }

  it('shows Restore first and folds the single-file exports under a link', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const backup = await screen.findByRole('region', { name: 'Backup' })
    expect(within(backup).queryByRole('heading', { name: 'Backup' })).not.toBeInTheDocument()
    const more = within(backup).getByRole('button', { name: 'More export options' })
    expect(within(backup).getByRole('button', { name: 'Restore…' })).toBeInTheDocument()
    expect(more).toHaveAttribute('aria-expanded', 'false')
    expect(within(backup).queryByRole('button', { name: /library\.json/ })).not.toBeInTheDocument()

    await fireEvent.click(more)

    expect(more).toHaveAttribute('aria-expanded', 'true')
    expect(within(backup).getByRole('button', { name: 'Library (library.json)' })).toBeInTheDocument()
    expect(within(backup).getByRole('button', { name: 'Settings (settings.json)' })).toBeInTheDocument()
  })

  it('downloads each export under the file name given by the server', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    const blob = new Blob(['{}'], { type: 'application/json' })
    apiDownload.mockResolvedValue({ blob, filename: 'library-2026-11-11.json' })
    URL.createObjectURL = vi.fn().mockReturnValue('blob:library')
    URL.revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    render(Settings, { props: {} })

    await openMoreExports()
    vi.useFakeTimers()
    await fireEvent.click(screen.getByRole('button', { name: 'Library (library.json)' }))
    await vi.waitFor(() => expect(click).toHaveBeenCalledOnce())

    expect(apiDownload).toHaveBeenCalledWith('/export/library')
    expect(URL.createObjectURL).toHaveBeenCalledWith(blob)
    expect(click.mock.contexts[0].download).toBe('library-2026-11-11.json')
    expect(URL.revokeObjectURL).not.toHaveBeenCalled()
    vi.advanceTimersByTime(40_000)
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:library')
    vi.useRealTimers()
    click.mockRestore()
  })

  it('exports the persisted settings', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    apiDownload.mockReturnValue(new Promise(() => {}))
    render(Settings, { props: {} })

    await openMoreExports()
    await fireEvent.click(screen.getByRole('button', { name: 'Settings (settings.json)' }))

    expect(apiDownload).toHaveBeenCalledWith('/export/settings')
  })

  it('shows the server error in a toast when an export fails', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    apiDownload.mockRejectedValue({ body: { detail: 'No library file to export.' } })
    const showToast = vi.spyOn(toastStore, 'showToast').mockImplementation(() => {})
    render(Settings, { props: {} })

    await openMoreExports()
    await fireEvent.click(screen.getByRole('button', { name: 'Library (library.json)' }))

    await vi.waitFor(() => expect(showToast).toHaveBeenCalledWith('⚠️ Export failed: No library file to export.'))
    showToast.mockRestore()
  })

  it('still offers the backup when loading the settings fails', async () => {
    apiGet.mockRejectedValue(new Error('Network error'))
    render(Settings, { props: {} })

    expect(await screen.findByText('Network error')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore…' })).toBeInTheDocument()
  })

  it('hides the backup while a setting is being edited', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    const row = (await screen.findByText('Admin API Port')).closest('tr')
    await fireEvent.click(within(row).getByRole('button', { name: 'Edit' }))

    expect(screen.queryByRole('heading', { name: 'Backup' })).not.toBeInTheDocument()
  })
})

describe('Settings — restore', () => {
  const libraryFile = new File(['{"discs": {}}'], 'library-2026-11-11.json', { type: 'application/json' })
  const settingsFile = new File(['{"schema_version": 1}'], 'settings-2026-11-11.json', { type: 'application/json' })
  const librarySummary = { disc_count: 2, added: ['tag-new'], changed: ['tag-changed'], removed: ['tag-old'] }
  const settingsSummary = {
    updated_paths: ['admin.api.port'],
    restart_required_paths: ['admin.api.port'],
    current_settings_error: null,
  }

  async function openRestore() {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })
    const restoreButton = await screen.findByRole('button', { name: 'Restore…' })
    // A real click focuses the button: the dialog gives the focus back to it when it closes.
    restoreButton.focus()
    await fireEvent.click(restoreButton)
    return screen.getByRole('dialog', { name: 'Restore a backup' })
  }

  async function chooseFile(dialog, file) {
    await fireEvent.change(within(dialog).getByLabelText('Backup file'), { target: { files: [file] } })
  }

  it('opens a modal dialog whose file input is never shown', async () => {
    const dialog = await openRestore()

    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(within(dialog).getByLabelText('Backup file')).not.toBeVisible()
    expect(within(dialog).getByRole('button', { name: /Drop a file here, or click to choose/ })).toBeVisible()
  })

  it('detects a library file and previews it before importing anything', async () => {
    apiUpload.mockResolvedValue(librarySummary)
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)

    expect(await within(dialog).findByText(/replaced by 2 discs/)).toBeInTheDocument()
    expect(apiUpload).toHaveBeenCalledExactlyOnceWith('/import/library/preview', libraryFile, {
      signal: expect.any(AbortSignal),
    })
    expect(within(dialog).getByText('library-2026-11-11.json')).toBeInTheDocument()
    expect(within(dialog).getByText('(tag-new)')).toBeInTheDocument()
    expect(within(dialog).getByText('(tag-old)')).toBeInTheDocument()
    expect(within(dialog).getByText('This replaces the current library. It cannot be undone.')).toBeInTheDocument()
  })

  it('detects a settings file dropped on the drop zone', async () => {
    apiUpload.mockResolvedValue(settingsSummary)
    const dialog = await openRestore()

    await fireEvent.drop(within(dialog).getByRole('button', { name: /Drop a file here/ }), {
      dataTransfer: { files: [settingsFile] },
    })

    expect(await within(dialog).findByText('admin.api.port')).toBeInTheDocument()
    expect(apiUpload).toHaveBeenCalledExactlyOnceWith('/import/settings/preview', settingsFile, {
      signal: expect.any(AbortSignal),
    })
  })

  it.each([
    [new File(['not json'], 'notes.txt'), 'notes.txt is not a JSON file: choose a library or a settings file.'],
    [new File(['[1, 2]'], 'list.json'), 'list.json is neither a library nor a settings file.'],
  ])('rejects a file that is not a library or settings file', async (file, message) => {
    const dialog = await openRestore()

    await chooseFile(dialog, file)

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(message)
    expect(apiUpload).not.toHaveBeenCalled()
    expect(within(dialog).queryByRole('button', { name: /Replace/ })).not.toBeInTheDocument()
  })

  it('sends a settings file without schema_version to the settings preview', async () => {
    apiUpload.mockResolvedValue(settingsSummary)
    const file = new File(['{"admin": {"api": {"port": 8100}}}'], 'old-settings.json')
    const dialog = await openRestore()

    await chooseFile(dialog, file)

    expect(await within(dialog).findByText('admin.api.port')).toBeInTheDocument()
    expect(apiUpload).toHaveBeenCalledExactlyOnceWith('/import/settings/preview', file, {
      signal: expect.any(AbortSignal),
    })
  })

  it('puts the focus in the review step, where Escape still closes the dialog', async () => {
    apiUpload.mockResolvedValue(librarySummary)
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)

    await vi.waitFor(() => expect(within(dialog).getByRole('heading', { name: 'Review the changes' })).toHaveFocus())
    await fireEvent.keyDown(document.body, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore…' })).toHaveFocus()
  })

  it('puts the focus back on the drop zone when choosing another file', async () => {
    apiUpload.mockResolvedValue(librarySummary)
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await fireEvent.click(await within(dialog).findByRole('button', { name: 'Choose another file' }))

    await vi.waitFor(() => expect(within(dialog).getByRole('button', { name: /Drop a file here/ })).toHaveFocus())
  })

  it('gives the focus back to Restore even when the click did not focus it (Safari, Firefox on macOS)', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    await fireEvent.click(await screen.findByRole('button', { name: 'Restore…' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(screen.getByRole('button', { name: 'Restore…' })).toHaveFocus()
  })

  it('closes during a pending preview and cancels it', async () => {
    apiUpload.mockReturnValue(new Promise(() => {}))
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await vi.waitFor(() => expect(apiUpload).toHaveBeenCalledOnce())
    const { signal } = apiUpload.mock.calls[0][2]
    expect(within(dialog).getByRole('button', { name: 'Close' })).toBeEnabled()
    await fireEvent.keyDown(document.body, { key: 'Escape' })

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(signal.aborted).toBe(true)
  })

  it('cannot be closed while a replacement is running', async () => {
    let finishImport
    apiUpload
      .mockResolvedValueOnce(librarySummary)
      .mockReturnValueOnce(new Promise((resolve) => (finishImport = resolve)))
    const showToast = vi.spyOn(toastStore, 'showToast').mockImplementation(() => {})
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await fireEvent.click(await within(dialog).findByRole('button', { name: 'Replace library' }))
    await fireEvent.keyDown(document.body, { key: 'Escape' })

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(within(dialog).getByRole('button', { name: 'Close' })).toBeDisabled()
    finishImport(librarySummary)
    await vi.waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    showToast.mockRestore()
  })

  it('shows the validation error of the server and offers no confirmation', async () => {
    apiUpload.mockRejectedValue({ body: { detail: 'Invalid library file: discs.t.uri Field required' } })
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Invalid library file: discs.t.uri')
    expect(within(dialog).queryByRole('button', { name: /Replace/ })).not.toBeInTheDocument()
  })

  it('imports the library only after confirmation, then gives focus back to Restore', async () => {
    apiUpload.mockResolvedValue(librarySummary)
    const showToast = vi.spyOn(toastStore, 'showToast').mockImplementation(() => {})
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await fireEvent.click(await within(dialog).findByRole('button', { name: 'Replace library' }))

    expect(apiUpload).toHaveBeenLastCalledWith('/import/library', libraryFile)
    await vi.waitFor(() => expect(showToast).toHaveBeenCalledWith('📚 Library imported: 2 discs.'))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Restore…' })).toHaveFocus()
    showToast.mockRestore()
  })

  it('reloads the settings after a settings import', async () => {
    apiUpload.mockResolvedValueOnce(settingsSummary).mockResolvedValueOnce({
      message: 'Settings imported. Changes take effect after restart.',
    })
    const showToast = vi.spyOn(toastStore, 'showToast').mockImplementation(() => {})
    const dialog = await openRestore()

    await chooseFile(dialog, settingsFile)
    expect(await within(dialog).findByText('Changes take effect after restart.')).toBeInTheDocument()
    await fireEvent.click(within(dialog).getByRole('button', { name: 'Replace settings' }))

    expect(apiUpload).toHaveBeenLastCalledWith('/import/settings', settingsFile)
    await vi.waitFor(() =>
      expect(showToast).toHaveBeenCalledWith('⚙️ Settings imported. Changes take effect after restart.'),
    )
    expect(apiGet).toHaveBeenCalledTimes(2)
    showToast.mockRestore()
  })

  it('imports nothing when cancelled', async () => {
    apiUpload.mockResolvedValue(librarySummary)
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await fireEvent.click(await within(dialog).findByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(apiUpload).toHaveBeenCalledExactlyOnceWith('/import/library/preview', libraryFile, {
      signal: expect.any(AbortSignal),
    })
  })

  it('goes back to the first step to choose another file', async () => {
    apiUpload.mockResolvedValue(librarySummary)
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await fireEvent.click(await within(dialog).findByRole('button', { name: 'Choose another file' }))

    expect(within(dialog).getByRole('button', { name: /Drop a file here/ })).toBeInTheDocument()
  })

  it('warns when the current settings file is invalid', async () => {
    apiUpload.mockResolvedValue({ ...settingsSummary, current_settings_error: 'Malformed settings file' })
    const dialog = await openRestore()

    await chooseFile(dialog, settingsFile)

    expect(await within(dialog).findByText(/current settings file is invalid and will be replaced/)).toBeInTheDocument()
  })

  it('keeps the dialog open with the error when the import fails', async () => {
    apiUpload
      .mockResolvedValueOnce(librarySummary)
      .mockRejectedValueOnce({ body: { detail: 'Server error: disk full' } })
    const dialog = await openRestore()

    await chooseFile(dialog, libraryFile)
    await fireEvent.click(await within(dialog).findByRole('button', { name: 'Replace library' }))

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Server error: disk full')
    expect(within(dialog).getByRole('button', { name: 'Replace library' })).toBeInTheDocument()
    await vi.waitFor(() => expect(within(dialog).getByRole('alert')).toHaveFocus())
  })
})
