// Pure filtering helpers for the Library table. They operate on `[tagId, disc]` entries
// (as returned by `Object.entries(discs)`) and never mutate their input.

import { typeLabel } from './discType.js'

export const ALL = ''
export const SHUFFLE_ON = 'on'
export const SHUFFLE_OFF = 'off'

/**
 * Distinct `display_type` values present in the library, sorted for a stable dropdown.
 * Derived from the data rather than hardcoded, so it follows whatever the API returns.
 */
export function typeOptions(entries) {
  const types = new Set(entries.map(([, disc]) => disc.display_type))
  return [...types].sort((a, b) => sortKey(a).localeCompare(sortKey(b)))
}

/**
 * Keeps the entries matching every active criterion. `ALL` (empty string) disables a criterion.
 * @param {Array<[string, object]>} entries
 * @param {{ type?: string, shuffle?: string }} criteria
 */
export function filterDiscs(entries, { type = ALL, shuffle = ALL } = {}) {
  return entries.filter(([, disc]) => {
    if (type !== ALL && disc.display_type !== type) return false
    if (shuffle === SHUFFLE_ON && !disc.option.shuffle) return false
    if (shuffle === SHUFFLE_OFF && disc.option.shuffle) return false
    return true
  })
}

export function isFiltering({ type = ALL, shuffle = ALL } = {}) {
  return type !== ALL || shuffle !== ALL
}

// Sort by the label after the leading emoji ("💿 Album" → "Album"), not by emoji code point.
function sortKey(displayType) {
  return typeLabel(displayType) || displayType
}
