// `display_type` comes from the API as "<emoji> <label>" (e.g. "💿 Album"). These helpers split it
// so the table and the filters agree on what the icon and the label are.

export function typeIcon(displayType) {
  return displayType.split(' ')[0]
}

/** The label after the leading emoji, or '' when there is none. */
export function typeLabel(displayType) {
  const spaceIndex = displayType.indexOf(' ')
  return spaceIndex === -1 ? '' : displayType.slice(spaceIndex + 1)
}
