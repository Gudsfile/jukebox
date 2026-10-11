import { render, screen, waitFor } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ReaderSlot from './ReaderSlot.svelte'

const disc = {
  uri: 'spotify:album:abc',
  metadata: { artist: 'Veridis Project', album: 'Voir le soleil', track: null, playlist: null },
  option: { shuffle: false, is_test: false },
  display_type: '💿 Album',
  display_title: 'Veridis Project — Voir le soleil',
}

describe('ReaderSlot', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('invites to place a disc when nothing is on the reader, with no action', () => {
    render(ReaderSlot, { props: { currentTag: null } })

    expect(screen.getByText('No disc detected')).toBeInTheDocument()
    expect(screen.getByText('Place a disc on the reader')).toBeInTheDocument()
    expect(screen.getByRole('button')).toHaveAccessibleName('Collapse reader') // only the toggle
  })

  it('offers to add an unknown disc', async () => {
    const onAdd = vi.fn()
    render(ReaderSlot, { props: { currentTag: { tag_id: 'tag-new', known_in_library: false }, onAdd } })

    expect(screen.getByText('Unknown disc')).toBeInTheDocument()
    expect(screen.getByText('tag-new')).toBeInTheDocument()
    expect(screen.getByText('New disc…')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Add this disc' }))
    expect(onAdd).toHaveBeenCalledWith('tag-new')
  })

  it('shows a known disc with its type, URI and title, and offers to edit it', async () => {
    const onEdit = vi.fn()
    render(ReaderSlot, { props: { currentTag: { tag_id: 'tag-1', known_in_library: true }, disc, onEdit } })

    expect(screen.getByText('Disc detected')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Album' })).toBeInTheDocument()
    expect(screen.getByText('spotify:album:abc')).toBeInTheDocument()
    expect(screen.getByText('Veridis Project — Voir le soleil')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Edit' }))
    expect(onEdit).toHaveBeenCalledWith('tag-1')
  })

  it('falls back to the tag id for a known tag whose library entry is not loaded', () => {
    render(ReaderSlot, { props: { currentTag: { tag_id: 'tag-cli', known_in_library: true } } })

    expect(screen.getByText('Disc detected')).toBeInTheDocument()
    expect(screen.getAllByText('tag-cli')).toHaveLength(2) // tag field + title fallback
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()
  })

  it('hides the action when actions are disabled', () => {
    render(ReaderSlot, {
      props: { currentTag: { tag_id: 'tag-new', known_in_library: false }, actionsEnabled: false },
    })

    expect(screen.getByRole('button')).toHaveAccessibleName('Collapse reader') // only the toggle
  })

  it('starts expanded, with a collapse toggle', () => {
    render(ReaderSlot, { props: { currentTag: null } })

    expect(screen.getByRole('button', { name: 'Collapse reader' })).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Place a disc on the reader')).toBeInTheDocument()
  })

  it('collapses to a bar with the status and title but no action, and expands back', async () => {
    render(ReaderSlot, { props: { currentTag: { tag_id: 'tag-1', known_in_library: true }, disc } })

    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))

    const expand = screen.getByRole('button', { name: 'Expand reader: Disc detected Veridis Project — Voir le soleil' })
    expect(expand).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByText('Disc detected')).toBeInTheDocument()
    expect(screen.getByText('Veridis Project — Voir le soleil')).toBeInTheDocument()
    expect(screen.queryByText('spotify:album:abc')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Edit' })).toBeNull()

    await fireEvent.click(expand)
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument()
  })

  it('keeps the chosen state across reloads', async () => {
    const first = render(ReaderSlot, { props: { currentTag: null } })
    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))
    first.unmount()

    render(ReaderSlot, { props: { currentTag: null } })
    expect(screen.getByRole('button', { name: /^Expand reader/ })).toBeInTheDocument()
  })

  it('saves the expanded state back when expanding', async () => {
    render(ReaderSlot, { props: { currentTag: null } })

    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))
    expect(localStorage.getItem('jukebox.readerSlot.collapsed')).toBe('true')

    await fireEvent.click(screen.getByRole('button', { name: /^Expand reader/ }))
    expect(localStorage.getItem('jukebox.readerSlot.collapsed')).toBe('false')
  })

  it('starts expanded and still toggles when storage is unavailable', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    render(ReaderSlot, { props: { currentTag: null } })
    expect(screen.getByRole('button', { name: 'Collapse reader' })).toHaveAttribute('aria-expanded', 'true')

    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))
    expect(screen.getByRole('button', { name: /^Expand reader/ })).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: /^Expand reader/ }))
    expect(screen.getByRole('button', { name: 'Collapse reader' })).toBeInTheDocument()
  })

  it('stays collapsed when the reader changes, updating its status', async () => {
    const { rerender } = render(ReaderSlot, { props: { currentTag: null } })
    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))

    await rerender({ currentTag: { tag_id: 'tag-new', known_in_library: false } })

    expect(screen.getByRole('button', { name: /^Expand reader/ })).toBeInTheDocument()
    expect(screen.getByText('Unknown disc')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Add this disc' })).toBeNull()
  })

  it('keeps keyboard focus on the toggle across the swap', async () => {
    render(ReaderSlot, { props: { currentTag: null } })

    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('button', { name: /^Expand reader/ })))

    await fireEvent.click(screen.getByRole('button', { name: /^Expand reader/ }))
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Collapse reader' })))
  })

  it('announces reader changes from one stable status node, not the toggles', async () => {
    const { rerender } = render(ReaderSlot, { props: { currentTag: null } })
    const status = screen.getByRole('status')
    expect(status).toHaveTextContent('No disc detected — Place a disc on the reader')
    expect(document.querySelectorAll('[aria-live], [role="status"]')).toHaveLength(1)

    await fireEvent.click(screen.getByRole('button', { name: 'Collapse reader' }))
    expect(screen.getByRole('status')).toBe(status)

    await rerender({ currentTag: { tag_id: 'tag-new', known_in_library: false } })
    expect(status).toHaveTextContent('Unknown disc — New disc…')
  })
})
