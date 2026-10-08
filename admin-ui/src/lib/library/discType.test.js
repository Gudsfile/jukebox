import { describe, expect, it } from 'vitest'
import { compareTypes, typeIcon, typeLabel } from './discType.js'

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

describe('compareTypes', () => {
  it('orders by label rather than by leading emoji', () => {
    expect(['🎵 Track', '💿 Album', '🎧 Playlist'].sort(compareTypes)).toEqual(['💿 Album', '🎧 Playlist', '🎵 Track'])
  })

  it('orders a type without a label by its whole value', () => {
    expect(['🎵 Track', 'Podcast', '💿 Album'].sort(compareTypes)).toEqual(['💿 Album', 'Podcast', '🎵 Track'])
  })
})
