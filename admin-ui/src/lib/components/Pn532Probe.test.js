import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Pn532Probe from './Pn532Probe.svelte'
import { apiPost } from '../api.js'

vi.mock('../api.js', () => ({
  apiPost: vi.fn(),
}))

const profiles = [
  {
    name: 'waveshare_hat',
    label: 'WaveShare PN532 NFC HAT',
    protocol: 'spi',
    defaults: { reset: 20, cs: 4, irq: null },
  },
]

const probed = {
  board_profile: 'waveshare_hat',
  protocol: 'spi',
  pins: { reset: 20, cs: 8, irq: null },
  firmware_version: '1.6',
  uid: '04:ab:cd:ef',
}

function probeDialog() {
  return screen.getByRole('dialog', { name: 'Probe the PN532 reader?' })
}

async function probe() {
  await fireEvent.click(screen.getByRole('button', { name: 'Probe' }))
  await fireEvent.click(within(probeDialog()).getByRole('button', { name: 'Probe' }))
}

beforeEach(() => {
  apiPost.mockReset()
})

describe('Pn532Probe', () => {
  it('warns that probing can disturb a running jukebox', () => {
    render(Pn532Probe, { props: { profiles } })

    expect(screen.getByText(/can disturb it: both use the same SPI bus/)).toBeInTheDocument()
  })

  it('asks for a confirmation before probing', async () => {
    render(Pn532Probe, { props: { profiles } })

    await fireEvent.click(screen.getByRole('button', { name: 'Probe' }))

    expect(within(probeDialog()).getByText(/can disturb it: both use the same SPI bus/)).toBeInTheDocument()
    expect(apiPost).not.toHaveBeenCalled()
  })

  it('does not probe when the confirmation is cancelled, and gives the focus back to Probe', async () => {
    render(Pn532Probe, { props: { profiles } })
    const button = screen.getByRole('button', { name: 'Probe' })

    await fireEvent.click(button)
    await fireEvent.click(within(probeDialog()).getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(apiPost).not.toHaveBeenCalled()
    expect(button).toHaveFocus()
  })

  it('shows the profile, protocol, pins, firmware version and tag UID once confirmed', async () => {
    apiPost.mockResolvedValue(probed)
    render(Pn532Probe, { props: { profiles } })

    await probe()

    expect(apiPost).toHaveBeenCalledWith('/pn532/probe')
    expect(await screen.findByText('Firmware version: 1.6')).toBeInTheDocument()
    expect(screen.getByText('Probed with: WaveShare PN532 NFC HAT, SPI')).toBeInTheDocument()
    expect(screen.getByText('Pins: Reset GPIO20, Chip select GPIO8, IRQ —')).toBeInTheDocument()
    expect(screen.getByText('Tag UID: 04:ab:cd:ef')).toBeInTheDocument()
  })

  it('says when no tag is on the reader', async () => {
    apiPost.mockResolvedValue({ ...probed, uid: null })
    render(Pn532Probe, { props: { profiles } })

    await probe()

    expect(await screen.findByText('No tag detected')).toBeInTheDocument()
  })

  it('shows the API error, such as the GPIO hint or the missing extra', async () => {
    const detail = 'GPIO error — your pin configuration may be incorrect (bad GPIO number).'
    apiPost.mockRejectedValue(Object.assign(new Error('API error 502'), { body: { detail } }))
    render(Pn532Probe, { props: { profiles } })

    await probe()

    expect(await screen.findByRole('alert')).toHaveTextContent(detail)
  })

  it('disables the button while probing', async () => {
    let resolve
    apiPost.mockReturnValue(new Promise((r) => (resolve = r)))
    render(Pn532Probe, { props: { profiles } })

    await probe()

    expect(screen.getByRole('button', { name: 'Probing…' })).toBeDisabled()
    resolve(probed)
    expect(await screen.findByRole('button', { name: 'Probe' })).toBeEnabled()
  })
})
