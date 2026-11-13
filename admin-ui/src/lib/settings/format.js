// Formats a setting value the way the Settings table displays it.
export function formatValue(value) {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const PROVENANCE_LABELS = {
  default: 'Default',
  file: 'Settings file',
  env: 'Environment override',
  cli: 'CLI override',
  mixed: 'Mixed source',
}

// Turns a setting provenance into a readable source label, keeping unknown values as they are.
export function formatProvenance(provenance) {
  return PROVENANCE_LABELS[provenance] ?? provenance
}

// An object value may overflow its capped box and scroll: make it reachable from the keyboard, under
// the given name. Other values stay out of the tab order, so a table row is not one stop per cell.
export function scrollableValueAttributes(value, label) {
  if (value === null || typeof value !== 'object') return {}
  return { tabindex: 0, role: 'group', 'aria-label': label }
}
