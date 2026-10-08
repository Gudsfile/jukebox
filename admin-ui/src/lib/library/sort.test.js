import { describe, expect, it } from 'vitest'
import { nextSort, sortEntries } from './sort.js'

function disc(displayType, displayTitle, shuffle = false) {
  return { display_type: displayType, display_title: displayTitle, option: { shuffle, is_test: false } }
}

const entries = [
  ['tag-10', disc('💿 Album', 'Zubi — Dear Z', true)],
  ['tag-2', disc('🎧 Playlist', 'abba gold')],
  ['Tag-1', disc('🎵 Track', 'Air — La femme d’argent', true)],
  ['tag-3', disc('🎤 Artist', 'Bonobo')],
]

const keys = (result) => result.map(([tagId]) => tagId)

describe('sortEntries', () => {
  it('keeps the original order when no sort is active', () => {
    expect(keys(sortEntries(entries, null))).toEqual(['tag-10', 'tag-2', 'Tag-1', 'tag-3'])
  })

  it('keeps the original order for an unknown key', () => {
    expect(keys(sortEntries(entries, { key: 'nope', direction: 'asc' }))).toEqual(keys(entries))
  })

  it('returns a new array and does not mutate the input', () => {
    const input = [...entries]
    const result = sortEntries(input, { key: 'tag', direction: 'desc' })
    expect(result).not.toBe(input)
    expect(input).toEqual(entries)
    expect(sortEntries(input, null)).not.toBe(input)
  })

  it('sorts tags naturally and case-insensitively', () => {
    expect(keys(sortEntries(entries, { key: 'tag', direction: 'asc' }))).toEqual(['Tag-1', 'tag-2', 'tag-3', 'tag-10'])
    expect(keys(sortEntries(entries, { key: 'tag', direction: 'desc' }))).toEqual(['tag-10', 'tag-3', 'tag-2', 'Tag-1'])
    // Tags differing only by case tie, so they keep their original order whichever comes first.
    const caseOnly = [
      ['Kitchen', disc('💿 Album', 'x')],
      ['kitchen', disc('💿 Album', 'y')],
    ]
    expect(keys(sortEntries(caseOnly, { key: 'tag', direction: 'asc' }))).toEqual(['Kitchen', 'kitchen'])
    expect(keys(sortEntries([...caseOnly].reverse(), { key: 'tag', direction: 'asc' }))).toEqual(['kitchen', 'Kitchen'])
  })

  it('sorts types by label, ignoring the leading emoji', () => {
    expect(keys(sortEntries(entries, { key: 'type', direction: 'asc' }))).toEqual(['tag-10', 'tag-3', 'tag-2', 'Tag-1'])
  })

  it('sorts a type without an emoji prefix by its whole value', () => {
    const withBareType = [['bare', disc('Podcast', 'x')], ...entries]
    expect(keys(sortEntries(withBareType, { key: 'type', direction: 'asc' }))).toEqual([
      'tag-10',
      'tag-3',
      'tag-2',
      'bare',
      'Tag-1',
    ])
  })

  it('sorts titles case-insensitively', () => {
    expect(keys(sortEntries(entries, { key: 'title', direction: 'asc' }))).toEqual([
      'tag-2',
      'Tag-1',
      'tag-3',
      'tag-10',
    ])
    expect(keys(sortEntries(entries, { key: 'title', direction: 'desc' }))).toEqual([
      'tag-10',
      'tag-3',
      'Tag-1',
      'tag-2',
    ])
  })

  it('sorts shuffle off before on, keeping the original order among ties', () => {
    expect(keys(sortEntries(entries, { key: 'shuffle', direction: 'asc' }))).toEqual([
      'tag-2',
      'tag-3',
      'tag-10',
      'Tag-1',
    ])
    expect(keys(sortEntries(entries, { key: 'shuffle', direction: 'desc' }))).toEqual([
      'tag-10',
      'Tag-1',
      'tag-2',
      'tag-3',
    ])
  })
})

describe('nextSort', () => {
  it('starts ascending on a new column', () => {
    expect(nextSort(null, 'tag')).toEqual({ key: 'tag', direction: 'asc' })
    expect(nextSort({ key: 'title', direction: 'desc' }, 'tag')).toEqual({ key: 'tag', direction: 'asc' })
  })

  it('cycles asc → desc → no sort on the same column', () => {
    expect(nextSort({ key: 'tag', direction: 'asc' }, 'tag')).toEqual({ key: 'tag', direction: 'desc' })
    expect(nextSort({ key: 'tag', direction: 'desc' }, 'tag')).toBeNull()
  })
})
