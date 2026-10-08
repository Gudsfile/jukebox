import { describe, expect, it } from 'vitest'
import { normalize, searchDiscs } from './search.js'

const entries = [
  [
    'tag-1',
    {
      uri: 'spotify:album:abc',
      metadata: { artist: 'Véridis Project', album: 'Voir le soleil', track: null, playlist: null },
      display_title: 'Véridis Project — Voir le soleil',
    },
  ],
  [
    'tag-2',
    {
      uri: 'spotify:playlist:xyz',
      metadata: { artist: null, album: null, track: null, playlist: 'Radio Night' },
      display_title: 'Radio Night',
    },
  ],
  [
    'kitchen',
    {
      uri: 'file:///music/Électro.mp3',
      metadata: { artist: 'Zubi', album: null, track: 'dey ok', playlist: null },
      display_title: 'Zubi — dey ok',
    },
  ],
]

const tags = (result) => result.map(([tagId]) => tagId)

describe('normalize', () => {
  it('lowercases and strips accents', () => {
    expect(normalize('ÉLECTRO Véridis')).toBe('electro veridis')
  })
})

describe('searchDiscs', () => {
  it('returns every entry for an empty or blank query', () => {
    expect(tags(searchDiscs(entries, ''))).toEqual(['tag-1', 'tag-2', 'kitchen'])
    expect(tags(searchDiscs(entries, '   '))).toEqual(['tag-1', 'tag-2', 'kitchen'])
    expect(tags(searchDiscs(entries, undefined))).toEqual(['tag-1', 'tag-2', 'kitchen'])
  })

  it('matches on the tag', () => {
    expect(tags(searchDiscs(entries, 'kitch'))).toEqual(['kitchen'])
  })

  it('matches on the title', () => {
    expect(tags(searchDiscs(entries, 'radio night'))).toEqual(['tag-2'])
  })

  it('matches on the artist', () => {
    expect(tags(searchDiscs(entries, 'zubi'))).toEqual(['kitchen'])
  })

  it('matches on the URI', () => {
    expect(tags(searchDiscs(entries, 'playlist:xyz'))).toEqual(['tag-2'])
  })

  it('is case-insensitive', () => {
    expect(tags(searchDiscs(entries, 'SOLEIL'))).toEqual(['tag-1'])
  })

  it('is accent-insensitive in both directions', () => {
    expect(tags(searchDiscs(entries, 'veridis'))).toEqual(['tag-1'])
    expect(tags(searchDiscs(entries, 'électro'))).toEqual(['kitchen'])
    expect(tags(searchDiscs(entries, 'electro'))).toEqual(['kitchen'])
  })

  it('requires every term to match, possibly across different fields', () => {
    expect(tags(searchDiscs(entries, 'zubi kitchen'))).toEqual(['kitchen'])
    expect(tags(searchDiscs(entries, 'zubi radio'))).toEqual([])
  })

  it('matches metadata hidden from the displayed title (album behind a track)', () => {
    const [tagId, disc] = entries[2]
    const withAlbum = [[tagId, { ...disc, metadata: { ...disc.metadata, album: 'Dear Z' } }]]
    expect(tags(searchDiscs(withAlbum, 'dear z'))).toEqual(['kitchen'])
  })

  it('does not match on non-text fields such as the display type', () => {
    const [tagId, disc] = entries[0]
    expect(searchDiscs([[tagId, { ...disc, display_type: '💿 Album' }]], '💿')).toEqual([])
  })

  it('tolerates a disc without metadata', () => {
    const bare = [['bare', { uri: 'spotify:track:1', display_title: '—' }]]
    expect(tags(searchDiscs(bare, 'track'))).toEqual(['bare'])
  })

  it('returns a new array and does not mutate the input', () => {
    const snapshot = structuredClone(entries)
    const result = searchDiscs(entries, '')
    expect(result).not.toBe(entries)
    searchDiscs(entries, 'zubi')
    expect(entries).toEqual(snapshot)
  })
})
