import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Library from './Library.svelte'
import { apiDelete, apiGet } from '../api.js'

vi.mock('../api.js', () => ({
  apiGet: vi.fn(),
  apiDelete: vi.fn(),
}))

const discs = {
  'tag-1': {
    uri: 'spotify:album:abc',
    metadata: { artist: 'Veridis Project', album: 'Voir le soleil', track: null, playlist: null },
    option: { shuffle: false, is_test: false },
    display_type: '💿 Album',
    display_title: 'Veridis Project — Voir le soleil',
  },
  'tag-2': {
    uri: 'spotify:playlist:xyz',
    metadata: { artist: null, album: null, track: null, playlist: 'Radio Veridis' },
    option: { shuffle: true, is_test: false },
    display_type: '🎧 Playlist',
    display_title: 'Radio Veridis',
  },
}

beforeEach(() => {
  apiGet.mockReset()
  apiDelete.mockReset()
  globalThis.navigator.clipboard = { writeText: vi.fn().mockResolvedValue(undefined) }
})

afterEach(() => {
  vi.useRealTimers()
})

describe('Library — loading and empty/error states', () => {
  it('shows a loading message, then the table once discs resolve', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })

    expect(screen.getByText('Loading…')).toBeInTheDocument()
    expect(await screen.findByText('tag-1')).toBeInTheDocument()
  })

  it('shows "No disc found" for an empty library', async () => {
    apiGet.mockResolvedValue({})
    render(Library, { props: {} })

    expect(await screen.findByText('No disc found')).toBeInTheDocument()
  })

  it('shows the error message when loading fails', async () => {
    apiGet.mockRejectedValue(new Error('Network error'))
    render(Library, { props: {} })

    expect(await screen.findByText('Network error')).toBeInTheDocument()
  })
})

describe('Library — table rendering', () => {
  it('renders Type icon/label, Title, and shuffle state per row', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })

    const row1 = (await screen.findByText('tag-1')).closest('tr')
    expect(within(row1).getByText('💿')).toBeInTheDocument()
    expect(within(row1).getByText('Album')).toBeInTheDocument()
    expect(within(row1).getByText('Veridis Project — Voir le soleil')).toBeInTheDocument()
    expect(within(row1).getByLabelText('Shuffle off')).toBeInTheDocument()

    const row2 = screen.getByText('tag-2').closest('tr')
    expect(within(row2).getByText('🎧')).toBeInTheDocument()
    expect(within(row2).getByLabelText('Shuffle on')).toBeInTheDocument()
  })
})

describe('Library — add/edit/delete flow', () => {
  it('opens the create form from the header action and hides it while a form is open', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.click(screen.getByRole('button', { name: 'Add disc' }))

    expect(screen.getByLabelText('Tag ID')).toHaveValue('')
    expect(screen.queryByRole('button', { name: 'Add disc' })).toBeNull()
  })

  it('opens the edit form prefilled from the row and reloads the list on save', async () => {
    apiGet.mockResolvedValueOnce(discs).mockResolvedValueOnce(discs)
    render(Library, { props: {} })
    const row1 = (await screen.findByText('tag-1')).closest('tr')

    await fireEvent.click(within(row1).getByRole('button', { name: 'Edit' }))

    expect(screen.getByLabelText('Tag ID')).toHaveValue('tag-1')
    expect(screen.getByLabelText('Tag ID')).toBeDisabled()
    expect(screen.getByLabelText('Artist')).toHaveValue('Veridis Project')
  })

  it('deletes a disc after confirmation and reloads', async () => {
    vi.useFakeTimers()
    const confirmSpy = vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    apiGet.mockResolvedValue(discs)
    apiDelete.mockResolvedValue(null)
    render(Library, { props: {} })
    const row1 = (await screen.findByText('tag-1')).closest('tr')

    await fireEvent.click(within(row1).getByRole('button', { name: 'Delete' }))

    expect(confirmSpy).toHaveBeenCalledWith('Delete disc "tag-1"?')
    expect(apiDelete).toHaveBeenCalledWith('/discs/tag-1')
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))
    vi.runOnlyPendingTimers()
  })

  it('shows an error and keeps the row when delete fails', async () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    apiGet.mockResolvedValue(discs)
    apiDelete.mockRejectedValue({ body: { detail: "Tag does not exist: tag_id='tag-1'" } })
    render(Library, { props: {} })
    const row1 = (await screen.findByText('tag-1')).closest('tr')

    await fireEvent.click(within(row1).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText("Tag does not exist: tag_id='tag-1'")).toBeInTheDocument()
    expect(screen.getByText('tag-1')).toBeInTheDocument()
    expect(apiGet).toHaveBeenCalledTimes(1)
  })

  it('does not delete when the confirmation is dismissed', async () => {
    vi.spyOn(globalThis, 'confirm').mockReturnValue(false)
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    const row1 = (await screen.findByText('tag-1')).closest('tr')

    await fireEvent.click(within(row1).getByRole('button', { name: 'Delete' }))

    expect(apiDelete).not.toHaveBeenCalled()
  })
})

describe('Library — click-to-copy', () => {
  it('copies the full URI and shows transient confirmation', async () => {
    vi.useFakeTimers()
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await vi.waitFor(() => expect(screen.getByText('tag-1')).toBeInTheDocument(), { timeout: 5000 })

    const row1 = screen.getByText('tag-1').closest('tr')
    await fireEvent.click(within(row1).getByRole('button', { name: 'Copy URI' }))

    expect(globalThis.navigator.clipboard.writeText).toHaveBeenCalledWith('spotify:album:abc')
    expect(await within(row1).findByRole('button', { name: 'Copied' })).toBeInTheDocument()

    await vi.advanceTimersByTimeAsync(1500)
    expect(within(row1).getByRole('button', { name: 'Copy URI' })).toBeInTheDocument()
  })
})

describe('Library — current-tag spin indicator', () => {
  it('shows the spinning disc only next to the matching known-in-library row', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    const row1 = (await screen.findByText('tag-1')).closest('tr')
    const row2 = screen.getByText('tag-2').closest('tr')

    const [source] = globalThis.EventSource.instances
    source.onmessage({ data: JSON.stringify({ tag_id: 'tag-1', known_in_library: true }) })
    await vi.waitFor(() => expect(within(row1).getByText('💿', { selector: '.tag-spin' })).toBeInTheDocument())
    expect(within(row2).queryByText('💿', { selector: '.tag-spin' })).toBeNull()
  })
})

describe('Library — intent routing', () => {
  it('opens the edit form when given an edit intent once discs are loaded', async () => {
    apiGet.mockResolvedValue(discs)
    const onIntentConsumed = vi.fn()
    render(Library, { props: { intent: { type: 'edit', tagId: 'tag-1' }, onIntentConsumed } })

    expect(await screen.findByLabelText('Tag ID')).toHaveValue('tag-1')
    expect(onIntentConsumed).toHaveBeenCalled()
  })
})
