import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Pn532Form from './Pn532Form.svelte'
import { apiPut } from '../api.js'

vi.mock('../api.js', () => ({
  apiPut: vi.fn(),
}))

const profiles = [
  {
    name: 'waveshare_hat',
    label: 'WaveShare PN532 NFC HAT',
    protocol: 'spi',
    defaults: { reset: 20, cs: 4, irq: null },
  },
  { name: 'hiletgo_v3', label: 'HiLetgo PN532 V3', protocol: 'spi', defaults: { reset: null, cs: 4, irq: null } },
  { name: 'custom', label: 'Custom', protocol: 'spi', defaults: { reset: null, cs: null, irq: null } },
]

const config = {
  board_profile: 'waveshare_hat',
  protocol: 'spi',
  overrides: { reset: null, cs: 8, irq: null },
  resolved: { reset: 20, cs: 8, irq: null },
  profiles,
}

function renderForm(props = {}) {
  return render(Pn532Form, { props: { config, onSaved: vi.fn(), onCancel: vi.fn(), ...props } })
}

beforeEach(() => {
  apiPut.mockReset()
})

describe('Pn532Form — prefill', () => {
  it('prefills the profile and the persisted pin overrides', () => {
    renderForm()

    expect(screen.getByLabelText('Board profile')).toHaveValue('waveshare_hat')
    expect(screen.getByLabelText('Chip select')).toHaveValue(8)
    expect(screen.getByLabelText('Reset')).toHaveValue(null)
  })

  it('shows the selected profile defaults as placeholders', async () => {
    renderForm()

    expect(screen.getByLabelText('Reset')).toHaveAttribute('placeholder', 'Profile default: GPIO20')

    await fireEvent.change(screen.getByLabelText('Board profile'), { target: { value: 'hiletgo_v3' } })

    expect(screen.getByLabelText('Reset')).toHaveAttribute('placeholder', 'Profile default: —')
  })
})

describe('Pn532Form — submit', () => {
  it('saves the profile with empty pins sent as null', async () => {
    const saved = { ...config, board_profile: 'hiletgo_v3' }
    apiPut.mockResolvedValue(saved)
    const onSaved = vi.fn()
    renderForm({ onSaved })

    await fireEvent.change(screen.getByLabelText('Board profile'), { target: { value: 'hiletgo_v3' } })
    await fireEvent.input(screen.getByLabelText('IRQ'), { target: { value: '25' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPut).toHaveBeenCalledWith('/pn532', {
      board_profile: 'hiletgo_v3',
      spi: { reset: null, cs: 8, irq: 25 },
    })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved, 'save'))
  })

  it('resets every pin override of the saved profile right away', async () => {
    const saved = { ...config, overrides: { reset: null, cs: null, irq: null } }
    apiPut.mockResolvedValue(saved)
    const onSaved = vi.fn()
    renderForm({ onSaved })

    await fireEvent.change(screen.getByLabelText('Board profile'), { target: { value: 'custom' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Reset' }))

    expect(apiPut).toHaveBeenCalledWith('/pn532', {
      board_profile: 'waveshare_hat',
      spi: { reset: null, cs: null, irq: null },
    })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledWith(saved, 'reset'))
  })

  it('styles Reset like the settings reset and hides it when no pin is overridden', () => {
    const { unmount } = renderForm()
    expect(screen.getByRole('button', { name: 'Reset' })).toHaveClass('btn-danger')
    unmount()

    renderForm({ config: { ...config, overrides: { reset: null, cs: null, irq: null } } })
    expect(screen.queryByRole('button', { name: 'Reset' })).toBeNull()
  })

  it('shows the API error detail when saving fails', async () => {
    apiPut.mockRejectedValue(Object.assign(new Error('API error 400'), { body: { detail: 'Invalid pin' } }))
    renderForm()

    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Invalid pin')).toBeInTheDocument()
  })

  it('calls onCancel when cancel is clicked', async () => {
    const onCancel = vi.fn()
    renderForm({ onCancel })

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalledOnce()
  })
})

describe('Pn532Form — pinout clicks', () => {
  // The hit circle carries its GPIO as an SVG <title> child, out of getByTitle's reach (direct <svg> children only).
  const clickPin = (title) => fireEvent.click(screen.getByText(title, { selector: 'title' }).parentElement)

  it('fills the last focused pin field with the clicked GPIO', async () => {
    renderForm()

    await fireEvent.focus(screen.getByLabelText('IRQ'))
    await clickPin('GPIO17 · pin 11')

    expect(screen.getByLabelText('IRQ')).toHaveValue(17)
    expect(screen.getByLabelText('Chip select')).toHaveValue(8)
  })

  it('clears the override when clicking the pin it already holds', async () => {
    renderForm()

    await fireEvent.focus(screen.getByLabelText('Chip select'))
    await clickPin('GPIO8 · pin 24')

    expect(screen.getByLabelText('Chip select')).toHaveValue(null)
  })

  it('clears the override when clicking the profile default', async () => {
    renderForm()

    await fireEvent.focus(screen.getByLabelText('Reset'))
    await clickPin('GPIO17 · pin 11')
    await clickPin('GPIO20 · pin 38')

    expect(screen.getByLabelText('Reset')).toHaveValue(null)
  })
})
