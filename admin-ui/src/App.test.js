import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App.svelte'

beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  })
})

describe('App', () => {
  it('shows the Library page by default and switches on nav clicks', async () => {
    render(App)

    expect(screen.getByRole('heading', { name: 'Library' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'settings' }))
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'sonos' }))
    expect(screen.getByRole('heading', { name: 'Sonos' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'library' }))
    expect(screen.getByRole('heading', { name: 'Library' })).toBeInTheDocument()
  })

  it('renders the footer link to the repo', () => {
    render(App)

    const link = screen.getByRole('link', { name: /View on GitHub/ })
    expect(link).toHaveAttribute('href', 'https://github.com/Gudsfile/jukebox')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('jumping to Library via the current-tag banner switches page and carries the intent', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          'tag-123': {
            uri: '/music/song.mp3',
            metadata: { artist: null, album: null, track: null, playlist: null },
            option: { shuffle: false, is_test: false },
            display_type: '💿 Album',
            display_title: '—',
          },
        }),
    })
    render(App)

    await fireEvent.click(screen.getByRole('button', { name: 'sonos' }))
    expect(screen.getByRole('heading', { name: 'Sonos' })).toBeInTheDocument()

    const [source] = globalThis.EventSource.instances
    source.onmessage({ data: JSON.stringify({ tag_id: 'tag-123', known_in_library: false }) })

    await fireEvent.click(await screen.findByRole('button', { name: 'Add this disc' }))

    expect(await screen.findByRole('heading', { name: 'Library' })).toBeInTheDocument()
    const tagIdInput = await screen.findByLabelText('Tag ID')
    expect(tagIdInput).toHaveValue('tag-123')
  })

  it('clicking Manage Speakers on the Settings page switches to the Sonos page', async () => {
    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes('/settings/displays')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () =>
            Promise.resolve({
              settings: [
                {
                  path: 'jukebox.player.sonos.selected_group',
                  label: 'Sonos Selected Group',
                  description: 'The Sonos speaker group used for playback.',
                  field_type: 'object',
                  section: 'player',
                  section_label: 'Player',
                  choices: [],
                  default_value: null,
                  persisted_value: null,
                  effective_value: null,
                  provenance: 'default',
                  is_persisted: false,
                  is_pinned_default: false,
                  requires_restart: false,
                  advanced: false,
                },
              ],
              effective_settings_error: null,
            }),
        })
      }
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) })
    })
    render(App)

    await fireEvent.click(screen.getByRole('button', { name: 'settings' }))
    await fireEvent.click(await screen.findByRole('button', { name: 'Manage Speakers 🔊' }))

    expect(await screen.findByRole('heading', { name: 'Sonos' })).toBeInTheDocument()
  })
})
