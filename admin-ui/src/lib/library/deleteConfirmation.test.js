import { describe, expect, it } from 'vitest'
import { deleteDiscMessage } from './deleteConfirmation.js'

describe('deleteDiscMessage', () => {
  it('names the disc by its title and its tag', () => {
    expect(deleteDiscMessage('tag-1', { display_title: 'Radio Veridis' })).toBe(
      'This removes “Radio Veridis” (tag-1) from the library. It cannot be undone.',
    )
  })

  it('falls back to the tag when the disc is unknown', () => {
    expect(deleteDiscMessage('tag-1', undefined)).toBe(
      'This removes “tag-1” (tag-1) from the library. It cannot be undone.',
    )
  })
})
