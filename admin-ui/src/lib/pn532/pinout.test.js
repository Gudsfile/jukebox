import { describe, expect, it } from 'vitest'
import { wiringFor } from './pinout.js'

const physicalPins = (wired, kind) => wired.filter((pin) => pin.kind === kind).map((pin) => pin.physical)

describe('wiringFor', () => {
  it('always wires the SPI bus', () => {
    const { wired } = wiringFor('custom', { reset: null, cs: null, irq: null })

    expect(physicalPins(wired, 'bus')).toEqual([19, 21, 23])
  })

  it('offers every 5V and ground pin to the Waveshare HAT, any one of each', () => {
    const { wired } = wiringFor('waveshare_hat', { reset: 20, cs: 4, irq: null })
    const power = wired.filter((pin) => pin.kind === 'power')

    expect(power.map((pin) => pin.physical)).toEqual([2, 4, 6, 9, 14, 20, 25, 30, 34, 39])
    expect(power.every((pin) => pin.anyOf)).toBe(true)
  })

  it('offers every 3V3 and ground pin to a hand-wired module, any one of each', () => {
    const { wired } = wiringFor('hiletgo_v3', { reset: null, cs: 4, irq: null })
    const power = wired.filter((pin) => pin.kind === 'power')

    expect(power.map((pin) => pin.physical)).toEqual([1, 17, 6, 9, 14, 20, 25, 30, 34, 39])
    expect(power.every((pin) => pin.anyOf)).toBe(true)
  })

  it('places the configurable pins on their physical header pin', () => {
    const { wired } = wiringFor('waveshare_hat', { reset: 20, cs: 4, irq: 17 })

    expect(wired.filter((pin) => pin.kind === 'signal')).toEqual([
      { physical: 38, label: 'RST', kind: 'signal', bcm: 20 },
      { physical: 7, label: 'CS', kind: 'signal', bcm: 4 },
      { physical: 11, label: 'IRQ', kind: 'signal', bcm: 17 },
    ])
  })

  it('reports a GPIO that is not on the 40-pin header', () => {
    expect(wiringFor('custom', { reset: null, cs: 30, irq: null }).unmapped).toEqual([{ key: 'cs', bcm: 30 }])
  })

  it('flags a pin the kernel SPI driver already claims', () => {
    expect(wiringFor('custom', { reset: null, cs: 8, irq: null }).claimed).toEqual([{ key: 'cs', bcm: 8 }])
    expect(wiringFor('custom', { reset: null, cs: 4, irq: null }).claimed).toEqual([])
  })
})
