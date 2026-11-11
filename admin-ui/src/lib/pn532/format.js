export const PIN_FIELDS = [
  { key: 'reset', label: 'Reset' },
  { key: 'cs', label: 'Chip select' },
  { key: 'irq', label: 'IRQ' },
]

export function profileLabel(profiles, name) {
  return profiles.find((profile) => profile.name === name)?.label ?? name
}

export function formatPin(pin) {
  return pin === null || pin === undefined ? '—' : `GPIO${pin}`
}
