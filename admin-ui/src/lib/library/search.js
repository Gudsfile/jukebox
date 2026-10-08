// Free-text search over Library entries: case- and accent-insensitive, every whitespace-separated
// term must match at least one of the tag, displayed title, metadata fields, or URI. A superset of
// the CLI's SearchDiscs use case (tag + metadata), so both never disagree on a hit.

export function normalize(text) {
  return text
    .normalize('NFD')
    .replace(/\p{Diacritic}/gu, '')
    .toLowerCase()
}

function searchableText(tagId, disc) {
  const { artist, album, track, playlist } = disc.metadata ?? {}
  return normalize([tagId, disc.display_title, artist, album, track, playlist, disc.uri].filter(Boolean).join('\n'))
}

export function searchDiscs(entries, query) {
  const terms = normalize(query ?? '')
    .split(/\s+/)
    .filter(Boolean)
  if (terms.length === 0) return [...entries]
  return entries.filter(([tagId, disc]) => {
    const haystack = searchableText(tagId, disc)
    return terms.every((term) => haystack.includes(term))
  })
}
