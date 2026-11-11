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
