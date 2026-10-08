import { describe, expect, it } from 'vitest'
import { typeIcon, typeLabel } from './discType.js'

describe('typeIcon', () => {
  it('returns the leading emoji', () => {
    expect(typeIcon('💿 Album')).toBe('💿')
  })

  it('returns the whole value when there is no label', () => {
    expect(typeIcon('💿')).toBe('💿')
  })
})

describe('typeLabel', () => {
  it('returns everything after the leading emoji', () => {
    expect(typeLabel('💿 Album')).toBe('Album')
    expect(typeLabel('🎧 Radio Playlist')).toBe('Radio Playlist')
  })

  it('returns an empty label when there is no space', () => {
    expect(typeLabel('💿')).toBe('')
  })
})
