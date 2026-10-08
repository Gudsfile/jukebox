import { describe, expect, it } from 'vitest'
import { ALL, SHUFFLE_OFF, SHUFFLE_ON, filterDiscs, isFiltering, typeOptions } from './filter.js'

function disc(displayType, shuffle) {
  return { uri: 'x', display_type: displayType, option: { shuffle, is_test: false } }
}

const entries = [
  ['tag-1', disc('💿 Album', false)],
  ['tag-2', disc('🎧 Playlist', true)],
  ['tag-3', disc('💿 Album', true)],
  ['tag-4', disc('🎵 Track', false)],
]

const tagIds = (result) => result.map(([tagId]) => tagId)

describe('typeOptions', () => {
  it('returns the distinct types present, sorted by label', () => {
    expect(typeOptions(entries)).toEqual(['💿 Album', '🎧 Playlist', '🎵 Track'])
  })

  it('returns an empty list for an empty library', () => {
    expect(typeOptions([])).toEqual([])
  })
})

describe('filterDiscs', () => {
  it('returns every entry when no criterion is set', () => {
    expect(tagIds(filterDiscs(entries))).toEqual(['tag-1', 'tag-2', 'tag-3', 'tag-4'])
    expect(tagIds(filterDiscs(entries, { type: ALL, shuffle: ALL }))).toHaveLength(4)
  })

  it('filters by type', () => {
    expect(tagIds(filterDiscs(entries, { type: '💿 Album' }))).toEqual(['tag-1', 'tag-3'])
  })

  it('filters by shuffle on/off', () => {
    expect(tagIds(filterDiscs(entries, { shuffle: SHUFFLE_ON }))).toEqual(['tag-2', 'tag-3'])
    expect(tagIds(filterDiscs(entries, { shuffle: SHUFFLE_OFF }))).toEqual(['tag-1', 'tag-4'])
  })

  it('combines criteria with AND', () => {
    expect(tagIds(filterDiscs(entries, { type: '💿 Album', shuffle: SHUFFLE_ON }))).toEqual(['tag-3'])
    expect(filterDiscs(entries, { type: '🎵 Track', shuffle: SHUFFLE_ON })).toEqual([])
  })

  it('preserves input order and does not mutate the input', () => {
    // Reversed so the expected order differs from the tag-id order a sort would produce.
    const reversed = [...entries].reverse()
    const snapshot = structuredClone(reversed)
    const result = filterDiscs(reversed, { shuffle: SHUFFLE_ON })
    expect(tagIds(result)).toEqual(['tag-3', 'tag-2'])
    expect(result).not.toBe(reversed)
    expect(reversed).toEqual(snapshot)
  })
})

describe('isFiltering', () => {
  it('is false only when every criterion is ALL', () => {
    expect(isFiltering({})).toBe(false)
    expect(isFiltering({ type: ALL, shuffle: ALL })).toBe(false)
    expect(isFiltering({ type: '💿 Album' })).toBe(true)
    expect(isFiltering({ shuffle: SHUFFLE_OFF })).toBe(true)
  })
})
