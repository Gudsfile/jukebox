import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { describe, expect, it, vi } from 'vitest'
import ConfirmDialog from './ConfirmDialog.svelte'

function renderDialog(options = {}) {
  const onConfirm = vi.fn()
  const onCancel = vi.fn()
  render(ConfirmDialog, {
    ...options,
    props: {
      title: 'Delete this disc?',
      message: 'This cannot be undone.',
      confirmLabel: 'Delete',
      onConfirm,
      onCancel,
    },
  })
  return { onConfirm, onCancel, dialog: screen.getByRole('dialog', { name: 'Delete this disc?' }) }
}

describe('ConfirmDialog', () => {
  it('shows the message in a modal dialog, with the confirm button styled as destructive', () => {
    const { dialog } = renderDialog()

    expect(dialog).toHaveAccessibleDescription('This cannot be undone.')
    expect(screen.getByRole('button', { name: 'Delete' })).toHaveClass('btn-danger')
  })

  it('runs the action only on the confirm button', async () => {
    const { onConfirm, onCancel } = renderDialog()

    await fireEvent.click(screen.getByRole('button', { name: 'Delete' }))

    expect(onConfirm).toHaveBeenCalledOnce()
    expect(onCancel).not.toHaveBeenCalled()
  })

  it('cancels on Cancel, on the close button and on Escape', async () => {
    const { onConfirm, onCancel } = renderDialog()

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Close' }))
    await fireEvent.keyDown(document.body, { key: 'Escape' })

    expect(onCancel).toHaveBeenCalledTimes(3)
    expect(onConfirm).not.toHaveBeenCalled()
  })

  it('does not submit a form it is rendered in', async () => {
    const form = document.createElement('form')
    const onSubmit = vi.fn((event) => event.preventDefault())
    form.addEventListener('submit', onSubmit)
    document.body.append(form)
    renderDialog({ target: form })

    for (const name of ['Cancel', 'Close', 'Delete']) {
      await fireEvent.click(screen.getByRole('button', { name }))
    }

    expect(onSubmit).not.toHaveBeenCalled()
    form.remove()
  })
})
