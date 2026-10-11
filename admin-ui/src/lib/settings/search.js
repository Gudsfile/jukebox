// Free-text search over setting displays, with the same rules as the Library search: case- and
// accent-insensitive, every whitespace-separated term must match at least one field the row
// displays (label, path, default/persisted/effective values as formatted, source).

import { normalize, searchTerms } from '../library/search.js'
import { formatValue } from './format.js'

function searchableText(setting) {
  return normalize(
    [
      setting.label,
      setting.path,
      formatValue(setting.default_value),
      setting.is_persisted ? formatValue(setting.persisted_value) : null,
      formatValue(setting.effective_value),
      setting.provenance,
    ]
      .filter(Boolean)
      .join('\n'),
  )
}

export function searchSettings(settings, query) {
  const terms = searchTerms(query)
  if (terms.length === 0) return [...settings]
  return settings.filter((setting) => {
    const haystack = searchableText(setting)
    return terms.every((term) => haystack.includes(term))
  })
}
