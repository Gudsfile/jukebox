import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Pn532 from './Pn532.svelte'
import { apiGet, apiPut } from '../api.js'

vi.mock('../api.js', () => ({
  apiGet: vi.fn(),
  apiPut: vi.fn(),
}))

const config = {
  board_profile: 'waveshare_hat',
  protocol: 'spi',
  overrides: { reset: null, cs: 8, irq: null },
  resolved: { reset: 20, cs: 8, irq: null },
  profiles: [
    {
      name: 'waveshare_hat',
      label: 'WaveShare PN532 NFC HAT',
      protocol: 'spi',
      defaults: { reset: 20, cs: 4, irq: null },
    },
    { name: 'hiletgo_v3', label: 'HiLetgo PN532 V3', protocol: 'spi', defaults: { reset: null, cs: 4, irq: null } },
    { name: 'custom', label: 'Custom', protocol: 'spi', defaults: { reset: null, cs: null, irq: null } },
  ],
}

beforeEach(() => {
  apiGet.mockReset()
  apiPut.mockReset()
})

describe('Pn532 — effective configuration', () => {
  it('shows the profile, protocol and resolved pins', async () => {
    apiGet.mockResolvedValue(config)
    render(Pn532)

    expect(await screen.findByText('Profile: WaveShare PN532 NFC HAT')).toBeInTheDocument()
    expect(apiGet).toHaveBeenCalledWith('/pn532')
    expect(screen.getByText('Protocol: SPI')).toBeInTheDocument()
    expect(screen.getByText('Reset: GPIO20')).toBeInTheDocument()
    expect(screen.getByText('IRQ: —')).toBeInTheDocument()
  })

  it('flags only the pins that override the profile default', async () => {
    apiGet.mockResolvedValue(config)
    render(Pn532)

    const chipSelect = await screen.findByText(/Chip select: GPIO8/)
    expect(chipSelect).toHaveTextContent('Override')
    expect(screen.getByText(/Reset: GPIO20/)).not.toHaveTextContent('Override')
  })

  it('shows the API error when the config cannot be loaded', async () => {
    apiGet.mockRejectedValue(Object.assign(new Error('API error 500'), { body: { detail: 'Server error: boom' } }))
    render(Pn532)

    expect(await screen.findByText('Server error: boom')).toBeInTheDocument()
  })
})

describe('Pn532 — edit', () => {
  it('opens the form and shows the saved config after saving', async () => {
    apiGet.mockResolvedValue(config)
    apiPut.mockResolvedValue({
      ...config,
      board_profile: 'hiletgo_v3',
      overrides: { reset: null, cs: null, irq: null },
      resolved: { reset: null, cs: 4, irq: null },
    })
    render(Pn532)

    await fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
    await fireEvent.change(screen.getByLabelText('Board profile'), { target: { value: 'hiletgo_v3' } })
    await fireEvent.input(screen.getByLabelText('Chip select'), { target: { value: '' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Profile: HiLetgo PN532 V3')).toBeInTheDocument()
    expect(screen.getByText(/Chip select: GPIO4/)).not.toHaveTextContent('Override')
  })

  it('goes back to the panel when cancelling', async () => {
    apiGet.mockResolvedValue(config)
    render(Pn532)

    await fireEvent.click(await screen.findByRole('button', { name: 'Edit' }))
    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(screen.getByText('Profile: WaveShare PN532 NFC HAT')).toBeInTheDocument()
  })
})
