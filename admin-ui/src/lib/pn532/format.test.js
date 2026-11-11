import { describe, expect, it } from 'vitest'
import { formatPin, profileLabel } from './format.js'

describe('profileLabel', () => {
  const profiles = [{ name: 'hiletgo_v3', label: 'HiLetgo PN532 V3' }]

  it('returns the label the API gives for a known profile', () => {
    expect(profileLabel(profiles, 'hiletgo_v3')).toBe('HiLetgo PN532 V3')
  })

  it('falls back to the raw name for an unknown profile', () => {
    expect(profileLabel(profiles, 'other_board')).toBe('other_board')
  })
})

describe('formatPin', () => {
  it('prefixes a pin number with GPIO', () => {
    expect(formatPin(4)).toBe('GPIO4')
    expect(formatPin(0)).toBe('GPIO0')
  })

  it('shows a dash for an unset pin', () => {
    expect(formatPin(null)).toBe('—')
  })
})
