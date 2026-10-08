import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { describe, expect, it, vi } from 'vitest'
import ReaderSlot from './ReaderSlot.svelte'

const disc = {
  uri: 'spotify:album:abc',
  metadata: { artist: 'Veridis Project', album: 'Voir le soleil', track: null, playlist: null },
  option: { shuffle: false, is_test: false },
  display_type: '💿 Album',
  display_title: 'Veridis Project — Voir le soleil',
}

describe('ReaderSlot', () => {
  it('invites to place a disc when nothing is on the reader, with no action', () => {
    render(ReaderSlot, { props: { currentTag: null } })

    expect(screen.getByText('No disc detected')).toBeInTheDocument()
    expect(screen.getByText('Place a disc on the reader')).toBeInTheDocument()
    expect(screen.queryByRole('button')).toBeNull()
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

    expect(screen.queryByRole('button')).toBeNull()
  })
})
