import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Sonos from './Sonos.svelte'
import { ApiError, apiGet, apiPost } from '../api.js'

vi.mock('../api.js', () => ({
  ApiError: class ApiError extends Error {
    constructor(status, body) {
      super(`API error ${status}`)
      this.status = status
      this.body = body
    }
  },
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}))

const speaker = { uid: 'RINCON_1', name: 'Kitchen', host: '192.168.1.10', household_id: 'h', is_visible: true }
const speaker2 = { uid: 'RINCON_2', name: 'Living Room', host: '192.168.1.11', household_id: 'h', is_visible: true }

beforeEach(() => {
  apiGet.mockReset()
  apiPost.mockReset()
})

describe('Sonos — no saved selection', () => {
  it('shows no-selection message and the discovered speakers table', async () => {
    apiGet.mockImplementation((path) =>
      path === '/sonos/selection'
        ? Promise.resolve({ selected_group: null, availability: { status: 'not_selected', members: [] } })
        : Promise.resolve([speaker]),
    )
    render(Sonos, { props: {} })

    expect(await screen.findByText('No Sonos speaker selection is currently saved.')).toBeInTheDocument()
    expect(screen.getByText('Kitchen')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear saved selection' })).toBeNull()
  })
})

describe('Sonos — saved selection', () => {
  const selection = {
    selected_group: { coordinator_uid: 'RINCON_1', members: [{ uid: 'RINCON_1' }] },
    availability: { status: 'partial', members: [{ uid: 'RINCON_1', status: 'available', speaker }] },
  }

  it('shows status, coordinator, and members, resolving names from discovered speakers', async () => {
    apiGet.mockImplementation((path) =>
      path === '/sonos/selection' ? Promise.resolve(selection) : Promise.resolve([speaker]),
    )
    render(Sonos, { props: {} })

    expect(await screen.findByText('Status: Partially available')).toBeInTheDocument()
    expect(screen.getByText('Coordinator: Kitchen [RINCON_1]')).toBeInTheDocument()
    expect(screen.getByText('Selection', { selector: 'th' })).toBeInTheDocument()
    expect(screen.getByText('Coordinator', { selector: 'td' })).toBeInTheDocument()
  })

  it('shows Available when every selected member is currently discoverable', async () => {
    const fullSelection = {
      selected_group: { coordinator_uid: 'RINCON_1', members: [{ uid: 'RINCON_1' }, { uid: 'RINCON_2' }] },
      availability: {
        status: 'available',
        members: [
          { uid: 'RINCON_1', status: 'available', speaker },
          { uid: 'RINCON_2', status: 'available', speaker: speaker2 },
        ],
      },
    }
    apiGet.mockImplementation((path) =>
      path === '/sonos/selection' ? Promise.resolve(fullSelection) : Promise.resolve([speaker, speaker2]),
    )
    render(Sonos, { props: {} })

    expect(await screen.findByText('Status: Available')).toBeInTheDocument()
    expect(screen.getByText('Coordinator: Kitchen [RINCON_1]')).toBeInTheDocument()
    expect(screen.getByText('Members: Kitchen [RINCON_1], Living Room [RINCON_2]')).toBeInTheDocument()
  })

  it('clears the saved selection and reloads', async () => {
    apiGet.mockImplementation((path) =>
      path === '/sonos/selection' ? Promise.resolve(selection) : Promise.resolve([speaker]),
    )
    apiPost.mockResolvedValue({})
    render(Sonos, { props: {} })
    await screen.findByRole('button', { name: 'Clear saved selection' })

    await fireEvent.click(screen.getByRole('button', { name: 'Clear saved selection' }))

    expect(apiPost).toHaveBeenCalledWith('/settings/reset', { path: 'jukebox.player.sonos.selected_group' })
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledWith('/sonos/selection'))
  })

  it('opens the edit form and returns to the summary on save', async () => {
    apiGet.mockImplementation((path) =>
      path === '/sonos/selection' ? Promise.resolve(selection) : Promise.resolve([speaker]),
    )
    render(Sonos, { props: {} })
    await screen.findByRole('button', { name: 'Edit selection' })

    await fireEvent.click(screen.getByRole('button', { name: 'Edit selection' }))

    expect(screen.getByRole('heading', { name: 'Edit Sonos Selection' })).toBeInTheDocument()
  })
})

describe('Sonos — discovery failure', () => {
  it('shows a discovery-unavailable message and hides the speakers table', async () => {
    apiGet.mockRejectedValue(new ApiError(502, { detail: 'Failed to discover Sonos speakers.' }))
    render(Sonos, { props: {} })

    expect(await screen.findByText(/Sonos discovery unavailable: Failed to discover Sonos speakers\./)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Discovered speakers' })).toBeNull()
  })

  it('shows a generic error for non-discovery failures', async () => {
    apiGet.mockRejectedValue(new Error('Network error'))
    render(Sonos, { props: {} })

    expect(await screen.findByText('Network error')).toBeInTheDocument()
  })
})
