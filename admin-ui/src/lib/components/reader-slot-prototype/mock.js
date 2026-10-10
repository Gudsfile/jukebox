// PROTOTYPE, throwaway: fake library and reader states, so the collapsed ReaderSlot variants can
// be judged on `npm run dev` without the Python API or an NFC reader.

export const MOCK_DISCS = {
  '04a1b2c3': {
    uri: 'spotify:album:4LH4d3cOWNNsVw41Gqt2kv',
    display_title: 'The Dark Side of the Moon — Pink Floyd',
    display_type: '💿 Album',
    option: { shuffle: false },
    metadata: { artist: 'Pink Floyd', album: 'The Dark Side of the Moon' },
  },
  '04d4e5f6': {
    uri: 'spotify:playlist:37i9dQZF1DXcBWIGoYBM5M',
    display_title: 'Today’s Top Hits, a very long playlist title that should be truncated nicely',
    display_type: '🎧 Playlist',
    option: { shuffle: true },
    metadata: { playlist: 'Today’s Top Hits' },
  },
  '04a7b8c9': {
    uri: 'spotify:track:7GhIk7Il098yCjg4BQjzvb',
    display_title: 'Never Gonna Give You Up — Rick Astley',
    display_type: '🎵 Track',
    option: { shuffle: false },
    metadata: { artist: 'Rick Astley', track: 'Never Gonna Give You Up' },
  },
}

export const READER_STATES = {
  empty: null,
  unknown: { tag_id: '04ffee99', known_in_library: false },
  known: { tag_id: '04a1b2c3', known_in_library: true },
  'known (long title)': { tag_id: '04d4e5f6', known_in_library: true },
}
