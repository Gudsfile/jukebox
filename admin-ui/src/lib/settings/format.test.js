import { describe, expect, it } from 'vitest'
import { formatProvenance, formatValue } from './format.js'

describe('formatValue', () => {
  it('formats null, objects and scalars', () => {
    expect(formatValue(null)).toBe('null')
    expect(formatValue(undefined)).toBe('null')
    expect(formatValue({ a: 1 })).toBe('{"a":1}')
    expect(formatValue(8000)).toBe('8000')
  })
})

describe('formatProvenance', () => {
  it('turns known provenances into readable source labels', () => {
    expect(formatProvenance('default')).toBe('Default')
    expect(formatProvenance('file')).toBe('Settings file')
    expect(formatProvenance('env')).toBe('Environment override')
    expect(formatProvenance('cli')).toBe('CLI override')
    expect(formatProvenance('mixed')).toBe('Mixed source')
  })

  it('keeps an unknown provenance as is', () => {
    expect(formatProvenance('runtime')).toBe('runtime')
  })
})
