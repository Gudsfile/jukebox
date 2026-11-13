import { PIN_FIELDS } from './format.js'

// BCM GPIO number -> physical pin on the 40-pin header.
export const BCM_TO_PHYSICAL = {
  2: 3,
  3: 5,
  4: 7,
  17: 11,
  27: 13,
  22: 15,
  10: 19,
  9: 21,
  11: 23,
  0: 27,
  5: 29,
  6: 31,
  13: 33,
  19: 35,
  26: 37,
  14: 8,
  15: 10,
  18: 12,
  23: 16,
  24: 18,
  25: 22,
  8: 24,
  7: 26,
  1: 28,
  12: 32,
  16: 36,
  20: 38,
  21: 40,
}

// SPI0 lines the PN532 always uses, whatever the profile (see docs/readers.md#wiring).
const SPI_BUS = [
  { physical: 19, label: 'MOSI', kind: 'bus' },
  { physical: 21, label: 'MISO', kind: 'bus' },
  { physical: 23, label: 'SCK', kind: 'bus' },
]

const GROUNDS = [6, 9, 14, 20, 25, 30, 34, 39]

// One supply pin and one ground are enough, whichever is free: `anyOf` marks the alternatives.
const powerPins = (label, pins) => pins.map((physical) => ({ physical, label, kind: 'power', anyOf: true }))

const WIRED_POWER = [...powerPins('3V3', [1, 17]), ...powerPins('GND', GROUNDS)]

// The Waveshare HAT regulates its own 3.3V from 5V; plugged in, it touches every one of these pins anyway.
const HAT_POWER = [...powerPins('5V', [2, 4]), ...powerPins('GND', GROUNDS)]

// GPIO8 (CE0) is claimed by the kernel SPI driver (/dev/spidev0.0): probing fails with `GPIO busy` (#261).
const KERNEL_CLAIMED = [8]

const SHORT_LABELS = { reset: 'RST', cs: 'CS', irq: 'IRQ' }

/**
 * Lists the header pins to highlight for a profile and its effective (BCM) pins.
 * Returns { wired: [{ physical, label, kind, bcm? }], unmapped: [{ key, bcm }], claimed: [{ key, bcm }] }.
 */
export function wiringFor(profileName, resolved) {
  const wired = [...SPI_BUS, ...(profileName === 'waveshare_hat' ? HAT_POWER : WIRED_POWER)]
  const unmapped = []
  const claimed = []
  for (const { key } of PIN_FIELDS) {
    const bcm = resolved[key]
    if (bcm === null || bcm === undefined) continue
    const physical = BCM_TO_PHYSICAL[bcm]
    if (physical === undefined) unmapped.push({ key, bcm })
    else wired.push({ physical, label: SHORT_LABELS[key], kind: 'signal', bcm })
    if (KERNEL_CLAIMED.includes(bcm)) claimed.push({ key, bcm })
  }
  return { wired, unmapped, claimed }
}
