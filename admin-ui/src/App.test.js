import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { tick } from 'svelte'
import App from './App.svelte'

beforeEach(() => {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
  })
})

function mockVersionResponse(response) {
  globalThis.fetch = vi
    .fn()
    .mockImplementation((url) =>
      Promise.resolve(
        url === '/api/v1/version' ? response : { ok: true, status: 200, json: () => Promise.resolve({}) },
      ),
    )
}

describe('App', () => {
  it('shows the Library page by default and switches on nav clicks', async () => {
    render(App)

    expect(screen.getByRole('heading', { name: 'Library' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'settings' }))
    expect(screen.getByRole('heading', { name: 'Settings' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'sonos' }))
    expect(screen.getByRole('heading', { name: 'Sonos' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'pn532' }))
    expect(screen.getByRole('heading', { name: 'PN532' })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'library' }))
    expect(screen.getByRole('heading', { name: 'Library' })).toBeInTheDocument()
  })

  it('renders the footer link to the repo', () => {
    render(App)

    const link = screen.getByRole('link', { name: 'view on GitHub' })
    expect(link).toHaveAttribute('href', 'https://github.com/Gudsfile/jukebox')
    expect(link).toHaveAttribute('target', '_blank')
  })

  it('shows the installed version in the footer, linked to its GitHub release', async () => {
    mockVersionResponse({ ok: true, status: 200, json: () => Promise.resolve({ version: '1.10.0.dev3' }) })
    render(App)

    const link = await screen.findByRole('link', { name: 'v1.10.0.dev3' })
    expect(link).toHaveAttribute('href', 'https://github.com/Gudsfile/jukebox/releases/tag/v1.10.0.dev3')
    expect(link).toHaveAttribute('target', '_blank')
    expect(screen.getByRole('contentinfo')).toHaveTextContent(
      /^Jukebox v1\.10\.0\.dev3 • made with ❤️ & 💿 • view on GitHub$/,
    )
    expect(within(screen.getByRole('contentinfo')).getAllByRole('link')).toHaveLength(2)
  })

  it('shows an unknown version as plain text, without link', async () => {
    mockVersionResponse({ ok: true, status: 200, json: () => Promise.resolve({ version: 'unknown' }) })
    render(App)

    const footer = screen.getByRole('contentinfo')
    await vi.waitFor(() => expect(footer).toHaveTextContent(/^Jukebox unknown • made with ❤️ & 💿 • view on GitHub$/))
    expect(within(footer).getAllByRole('link')).toHaveLength(1)
  })

  it('shows no version and no toast when the version request fails', async () => {
    mockVersionResponse({ ok: false, status: 500, json: () => Promise.resolve(null) })
    render(App)

    // Let the rejected request reach the catch in onMount before asserting.
    await new Promise((resolve) => setTimeout(resolve))
    await tick()

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/version', expect.anything())
    const footer = screen.getByRole('contentinfo')
    expect(footer).toHaveTextContent(/^Jukebox made with ❤️ & 💿 • view on GitHub$/)
    expect(within(footer).getAllByRole('link')).toHaveLength(1)
    expect(screen.queryByRole('button', { name: 'Close toast' })).not.toBeInTheDocument()
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
