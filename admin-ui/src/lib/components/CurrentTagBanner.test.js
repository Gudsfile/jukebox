import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { tick } from 'svelte'
import { describe, expect, it, vi } from 'vitest'
import CurrentTagBanner from './CurrentTagBanner.svelte'

function emitCurrentTag(data) {
  const [source] = globalThis.EventSource.instances
  source.onmessage({ data: JSON.stringify(data) })
}

describe('CurrentTagBanner', () => {
  it('renders nothing before any SSE message arrives', () => {
    render(CurrentTagBanner)

    expect(screen.queryByText(/on reader/)).toBeNull()
  })

  it('shows the known-disc state and triggers onEditDisc', async () => {
    const onEditDisc = vi.fn()
    render(CurrentTagBanner, { props: { onEditDisc } })

    emitCurrentTag({ tag_id: 'tag-123', known_in_library: true })

    expect(await screen.findByText('Known disc on reader')).toBeInTheDocument()
    expect(screen.getByText(/already in the library/)).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Edit this disc' }))
    expect(onEditDisc).toHaveBeenCalledWith('tag-123')
  })

  it('shows the unknown-disc state and triggers onAddDisc', async () => {
    const onAddDisc = vi.fn()
    render(CurrentTagBanner, { props: { onAddDisc } })

    emitCurrentTag({ tag_id: 'tag-456', known_in_library: false })

    expect(await screen.findByText('Unknown disc on reader')).toBeInTheDocument()

    await fireEvent.click(screen.getByRole('button', { name: 'Add this disc' }))
    expect(onAddDisc).toHaveBeenCalledWith('tag-456')
  })

  it('renders nothing again once the tag is removed (null payload)', async () => {
    render(CurrentTagBanner)

    emitCurrentTag({ tag_id: 'tag-123', known_in_library: true })
    expect(await screen.findByText('Known disc on reader')).toBeInTheDocument()

    emitCurrentTag(null)
    await tick()
    expect(screen.queryByText(/on reader/)).toBeNull()
  })
})
