import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { copyText } from './clipboard.js'

describe('copyText', () => {
  let originalClipboard

  beforeEach(() => {
    originalClipboard = navigator.clipboard
    document.execCommand = vi.fn()
  })

  afterEach(() => {
    navigator.clipboard = originalClipboard
    delete document.execCommand
    document.body.innerHTML = ''
  })

  it('uses the Clipboard API when available', async () => {
    navigator.clipboard = { writeText: vi.fn().mockResolvedValue(undefined) }

    await copyText('spotify:album:abc')

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('spotify:album:abc')
    expect(document.execCommand).not.toHaveBeenCalled()
  })

  it('falls back to execCommand on a temporary textarea without the Clipboard API', async () => {
    navigator.clipboard = undefined
    const button = document.createElement('button')
    document.body.appendChild(button)
    button.focus()
    let copied = null
    document.execCommand.mockImplementation((command) => {
      copied = document.querySelector('textarea').value
      return command === 'copy'
    })

    await copyText('spotify:album:abc')

    expect(document.execCommand).toHaveBeenCalledWith('copy')
    expect(copied).toBe('spotify:album:abc')
    expect(document.querySelector('textarea')).toBeNull()
    expect(document.activeElement).toBe(button)
  })

  it('rejects and removes the textarea when execCommand fails', async () => {
    navigator.clipboard = undefined
    document.execCommand.mockReturnValue(false)

    await expect(copyText('spotify:album:abc')).rejects.toThrow()
    expect(document.querySelector('textarea')).toBeNull()
  })

  it('falls back to execCommand when the Clipboard API rejects', async () => {
    navigator.clipboard = { writeText: vi.fn().mockRejectedValue(new Error('denied')) }
    document.execCommand.mockReturnValue(true)

    await copyText('spotify:album:abc')

    expect(document.execCommand).toHaveBeenCalledWith('copy')
  })

  it('rejects when both the Clipboard API and execCommand fail', async () => {
    navigator.clipboard = { writeText: vi.fn().mockRejectedValue(new Error('denied')) }
    document.execCommand.mockReturnValue(false)

    await expect(copyText('spotify:album:abc')).rejects.toThrow()
  })
})
