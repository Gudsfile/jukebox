import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { createRawSnippet } from 'svelte'
import { describe, expect, it, vi } from 'vitest'
import Modal from './Modal.svelte'

const body = createRawSnippet(() => ({
  render: () => '<div><button>First</button><input hidden aria-label="Hidden" /><button>Last</button></div>',
}))

function renderModal(props = {}) {
  const onClose = vi.fn()
  const result = render(Modal, { props: { title: 'Restore a backup', onClose, children: body, ...props } })
  return { ...result, onClose, dialog: screen.getByRole('dialog', { name: 'Restore a backup' }) }
}

describe('Modal', () => {
  it('is a labelled modal dialog that takes the focus', () => {
    const { dialog } = renderModal()

    expect(dialog).toHaveAttribute('aria-modal', 'true')
    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus()
  })

  it('closes on Escape even when the focus fell on the page', async () => {
    const { onClose } = renderModal()
    document.body.focus()

    await fireEvent.keyDown(document.body, { key: 'Escape' })

    expect(onClose).toHaveBeenCalledOnce()
  })

  it('closes on the close button and on a press and release on the backdrop', async () => {
    const { onClose, container } = renderModal()
    const backdrop = container.querySelector('.modal-backdrop')

    await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    await fireEvent.mouseDown(backdrop)
    await fireEvent.click(backdrop)
    await fireEvent.click(screen.getByRole('button', { name: 'First' }))

    expect(onClose).toHaveBeenCalledTimes(2)
  })

  it('stays open when a text selection started in the dialog ends on the backdrop', async () => {
    const { onClose, container, dialog } = renderModal()

    await fireEvent.mouseDown(dialog)
    await fireEvent.click(container.querySelector('.modal-backdrop'))

    expect(onClose).not.toHaveBeenCalled()
  })

  it('ignores every close request while not closable', async () => {
    const { onClose, container } = renderModal({ closable: false })
    const backdrop = container.querySelector('.modal-backdrop')

    await fireEvent.keyDown(document.body, { key: 'Escape' })
    await fireEvent.mouseDown(backdrop)
    await fireEvent.click(backdrop)

    expect(screen.getByRole('button', { name: 'Close' })).toBeDisabled()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('traps the focus, skipping hidden elements', async () => {
    renderModal()
    const close = screen.getByRole('button', { name: 'Close' })
    const last = screen.getByRole('button', { name: 'Last' })

    last.focus()
    await fireEvent.keyDown(last, { key: 'Tab' })
    expect(close).toHaveFocus()

    await fireEvent.keyDown(close, { key: 'Tab', shiftKey: true })
    expect(last).toHaveFocus()
  })

  it('brings the focus back in when it fell on the page', async () => {
    renderModal()
    document.activeElement.blur()

    await fireEvent.keyDown(document.body, { key: 'Tab' })

    expect(screen.getByRole('button', { name: 'Close' })).toHaveFocus()
  })

  it('keeps a file dropped next to the drop zone from being opened by the browser', async () => {
    const { container } = renderModal()
    const backdrop = container.querySelector('.modal-backdrop')

    expect(fireEvent.dragOver(backdrop)).toBe(false)
    expect(fireEvent.drop(backdrop)).toBe(false)
  })

  it('gives the focus back to the element that opened it', () => {
    const opener = document.createElement('button')
    document.body.append(opener)
    opener.focus()

    const { unmount } = renderModal()
    expect(opener).not.toHaveFocus()
    unmount()

    expect(opener).toHaveFocus()
    opener.remove()
  })

  it('gives the focus back to the given opener even if it was not focused', () => {
    const opener = document.createElement('button')
    document.body.append(opener)

    const { unmount } = renderModal({ returnFocus: opener })
    unmount()

    expect(opener).toHaveFocus()
    opener.remove()
  })
})
