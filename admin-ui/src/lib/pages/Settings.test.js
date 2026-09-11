import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Settings from './Settings.svelte'
import { apiGet } from '../api.js'

vi.mock('../api.js', () => ({
  apiGet: vi.fn(),
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
  ],
  effective_settings_error: null,
}

beforeEach(() => {
  apiGet.mockReset()
})

describe('Settings — list', () => {
  it('groups settings by section and shows the effective value + source', async () => {
    apiGet.mockResolvedValue(displaysResponse)
    render(Settings, { props: {} })

    expect(await screen.findByRole('heading', { name: 'Paths' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Admin' })).toBeInTheDocument()
    expect(screen.getByText('Library Path')).toBeInTheDocument()
    expect(screen.getAllByText('9000')).toHaveLength(2)
    expect(screen.getByText('file')).toBeInTheDocument()
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
})
