// `display_type` comes from the API as "<emoji> <label>" (e.g. "💿 Album"). These helpers split it
// so the table, the filters and the sort agree on what the icon and the label are.

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' })

export function typeIcon(displayType) {
  return displayType.split(' ')[0]
}

/** The label after the leading emoji, or '' when there is none. */
export function typeLabel(displayType) {
  const spaceIndex = displayType.indexOf(' ')
  return spaceIndex === -1 ? '' : displayType.slice(spaceIndex + 1)
}

/**
 * Orders two `display_type` values by label, otherwise the emoji codepoint decides the order
 * (🎧 < 🎤 < 🎵 < 💿), which looks random to a user. A type without a label sorts by its whole value.
 */
export function compareTypes(a, b) {
  return collator.compare(typeLabel(a) || a, typeLabel(b) || b)
}
