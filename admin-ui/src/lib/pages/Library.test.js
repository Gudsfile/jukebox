import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import Library from './Library.svelte'
import { SHUFFLE_OFF, SHUFFLE_ON } from '../library/filter.js'
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

// Tag of each body row, in display order (the first row is the header).
const rowTags = () =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((row) => row.querySelector('.tag').textContent)

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

describe('Library — search', () => {
  it('narrows the table to matching rows as the query is typed', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.input(screen.getByRole('searchbox', { name: 'Search discs' }), {
      target: { value: 'VOIR' },
    })

    expect(screen.getByText('tag-1')).toBeInTheDocument()
    expect(screen.queryByText('tag-2')).toBeNull()
  })

  it('shows a no-results row distinct from the empty-library message', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.input(screen.getByRole('searchbox', { name: 'Search discs' }), {
      target: { value: 'nothing here' },
    })

    expect(screen.getByText('No disc matches “nothing here”')).toBeInTheDocument()
    expect(screen.queryByText('No disc found')).toBeNull()
    expect(screen.getByRole('searchbox', { name: 'Search discs' })).toHaveValue('nothing here')
  })

  it('shows every row again once the query is cleared', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')
    const searchbox = screen.getByRole('searchbox', { name: 'Search discs' })

    await fireEvent.input(searchbox, { target: { value: 'VOIR' } })
    expect(screen.queryByText('tag-2')).toBeNull()

    await fireEvent.input(searchbox, { target: { value: '' } })
    expect(screen.getByText('tag-1')).toBeInTheDocument()
    expect(screen.getByText('tag-2')).toBeInTheDocument()
  })

  it('edits the disc of a row narrowed by the search', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.input(screen.getByRole('searchbox', { name: 'Search discs' }), {
      target: { value: 'playlist' },
    })
    const row = screen.getByText('tag-2').closest('tr')
    await fireEvent.click(within(row).getByRole('button', { name: 'Edit' }))

    expect(screen.getByLabelText('Tag ID')).toHaveValue('tag-2')
  })

  it('deletes the disc of a row narrowed by the search', async () => {
    vi.useFakeTimers()
    const confirmSpy = vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    apiGet.mockResolvedValue(discs)
    apiDelete.mockResolvedValue(null)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.input(screen.getByRole('searchbox', { name: 'Search discs' }), {
      target: { value: 'playlist' },
    })
    const row = screen.getByText('tag-2').closest('tr')
    await fireEvent.click(within(row).getByRole('button', { name: 'Delete' }))

    expect(confirmSpy).toHaveBeenCalledWith('Delete disc "tag-2"?')
    expect(apiDelete).toHaveBeenCalledWith('/discs/tag-2')
    await vi.waitFor(() => expect(apiGet).toHaveBeenCalledTimes(2))
    vi.runOnlyPendingTimers()
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

describe('Library — filters', () => {
  it('shows every disc by default and offers only the types present in the library', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    expect(screen.getByText('tag-2')).toBeInTheDocument()
    const typeSelect = screen.getByLabelText('Type')
    expect(typeSelect).toHaveValue('')
    expect(screen.getByLabelText('Shuffle')).toHaveValue('')
    expect(
      within(typeSelect)
        .getAllByRole('option')
        .map((option) => option.textContent),
    ).toEqual(['All types', '💿 Album', '🎧 Playlist'])
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('filters rows by type', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.change(screen.getByLabelText('Type'), { target: { value: '🎧 Playlist' } })

    expect(screen.queryByText('tag-1')).toBeNull()
    expect(screen.getByText('tag-2')).toBeInTheDocument()
  })

  it('filters rows by shuffle state', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.change(screen.getByLabelText('Shuffle'), { target: { value: SHUFFLE_OFF } })

    expect(screen.getByText('tag-1')).toBeInTheDocument()
    expect(screen.queryByText('tag-2')).toBeNull()
  })

  it('shows a no-match message distinct from an empty library, and clears filters', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.change(screen.getByLabelText('Type'), { target: { value: '💿 Album' } })
    await fireEvent.change(screen.getByLabelText('Shuffle'), { target: { value: SHUFFLE_ON } })

    expect(screen.getByText('No disc matches the current filters')).toBeInTheDocument()
    expect(screen.queryByText('No disc found')).toBeNull()

    await fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))

    expect(screen.getByText('tag-1')).toBeInTheDocument()
    expect(screen.getByText('tag-2')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
  })

  it('moves focus to the Type filter after clearing, since the Clear button goes away', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.change(screen.getByLabelText('Shuffle'), { target: { value: SHUFFLE_ON } })
    const clearButton = screen.getByRole('button', { name: 'Clear filters' })
    clearButton.focus()
    await fireEvent.click(clearButton)

    expect(screen.getByLabelText('Type')).toHaveFocus()
  })

  it('falls back to all types when the filtered type leaves the library', async () => {
    vi.useFakeTimers()
    apiGet.mockResolvedValueOnce(discs).mockResolvedValueOnce({ 'tag-1': discs['tag-1'] })
    vi.spyOn(globalThis, 'confirm').mockReturnValue(true)
    apiDelete.mockResolvedValue(null)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.change(screen.getByLabelText('Type'), { target: { value: '🎧 Playlist' } })
    const row2 = screen.getByText('tag-2').closest('tr')
    await fireEvent.click(within(row2).getByRole('button', { name: 'Delete' }))

    expect(await screen.findByText('tag-1')).toBeInTheDocument()
    expect(screen.getByLabelText('Type')).toHaveValue('')
    expect(screen.queryByRole('button', { name: 'Clear filters' })).toBeNull()
    vi.runOnlyPendingTimers()
  })
})

describe('Library — search combined with filters', () => {
  it('applies the search and the filters together, and names both when nothing matches', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.input(screen.getByRole('searchbox', { name: 'Search discs' }), {
      target: { value: 'veridis' },
    })
    await fireEvent.change(screen.getByLabelText('Type'), { target: { value: '🎧 Playlist' } })

    expect(screen.queryByText('tag-1')).toBeNull()
    expect(screen.getByText('tag-2')).toBeInTheDocument()

    await fireEvent.change(screen.getByLabelText('Shuffle'), { target: { value: SHUFFLE_OFF } })

    expect(screen.getByText('No disc matches “veridis” with the current filters')).toBeInTheDocument()
  })
})

describe('Library — column sorting', () => {
  it('keeps the library order and marks no column as sorted by default', async () => {
    apiGet.mockResolvedValue({ 'tag-2': discs['tag-2'], 'tag-1': discs['tag-1'] })
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    expect(rowTags()).toEqual(['tag-2', 'tag-1'])
    expect(document.querySelector('th[aria-sort]')).toBeNull()
  })

  it('cycles a column through ascending, descending, then back to the default order', async () => {
    apiGet.mockResolvedValue({ 'tag-2': discs['tag-2'], 'tag-1': discs['tag-1'] })
    render(Library, { props: {} })
    await screen.findByText('tag-1')
    const tagButton = screen.getByRole('button', { name: 'Tag' })
    const tagHeader = tagButton.closest('th')

    await fireEvent.click(tagButton)
    expect(rowTags()).toEqual(['tag-1', 'tag-2'])
    expect(tagHeader).toHaveAttribute('aria-sort', 'ascending')
    expect(tagHeader.querySelector('.sort-indicator')).toHaveTextContent('▲')

    await fireEvent.click(tagButton)
    expect(rowTags()).toEqual(['tag-2', 'tag-1'])
    expect(tagHeader).toHaveAttribute('aria-sort', 'descending')
    expect(tagHeader.querySelector('.sort-indicator')).toHaveTextContent('▼')

    await fireEvent.click(tagButton)
    expect(rowTags()).toEqual(['tag-2', 'tag-1'])
    expect(tagHeader).not.toHaveAttribute('aria-sort')
    expect(tagHeader.querySelector('.sort-indicator')).toHaveTextContent('↕')
  })

  it('moves aria-sort to the newly sorted column', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.click(screen.getByRole('button', { name: 'Tag' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Title' }))

    expect(screen.getByRole('button', { name: 'Title' }).closest('th')).toHaveAttribute('aria-sort', 'ascending')
    expect(screen.getByRole('button', { name: 'Tag' }).closest('th')).not.toHaveAttribute('aria-sort')
    expect(rowTags()).toEqual(['tag-2', 'tag-1'])
  })

  it('does not make the URI column sortable', async () => {
    apiGet.mockResolvedValue(discs)
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    expect(screen.queryByRole('button', { name: 'URI' })).toBeNull()
  })
})

describe('Library — sorting combined with search and filters', () => {
  it('sorts only the rows left by the search and filters', async () => {
    apiGet.mockResolvedValue({
      ...discs,
      'tag-3': { ...discs['tag-2'], display_title: 'Another Veridis mix', uri: 'spotify:playlist:def' },
    })
    render(Library, { props: {} })
    await screen.findByText('tag-1')

    await fireEvent.input(screen.getByRole('searchbox', { name: 'Search discs' }), {
      target: { value: 'veridis' },
    })
    await fireEvent.change(screen.getByLabelText('Type'), { target: { value: '🎧 Playlist' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Title' }))

    expect(rowTags()).toEqual(['tag-3', 'tag-2'])
  })
})
