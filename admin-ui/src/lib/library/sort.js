// Column sorting for the Library table. Operates on `[tagId, disc]` entries (as returned by
// `Object.entries(discs)`) and never mutates its input.

import { compareTypes } from './discType.js'

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })

const comparators = {
  tag: ([a], [b]) => collator.compare(a, b),
  type: ([, a], [, b]) => compareTypes(a.display_type, b.display_type),
  title: ([, a], [, b]) => collator.compare(a.display_title, b.display_title),
  shuffle: ([, a], [, b]) => Number(a.option.shuffle) - Number(b.option.shuffle),
}

/**
 * Returns a new array of entries sorted by `sort.key` in `sort.direction` ('asc' | 'desc').
 * With no sort (`null`), the original order is kept. Sorting is stable, so ties keep their
 * original relative order in both directions.
 */
export function sortEntries(entries, sort) {
  const compare = sort && comparators[sort.key]
  if (!compare) return [...entries]
  const sign = sort.direction === 'desc' ? -1 : 1
  return [...entries].sort((a, b) => sign * compare(a, b))
}

/**
 * Next sort state when the header of column `key` is clicked: a new column starts ascending,
 * then descending, then back to no sort (the default order).
 */
export function nextSort(current, key) {
  if (current?.key !== key) return { key, direction: 'asc' }
  if (current.direction === 'asc') return { key, direction: 'desc' }
  return null
}
