import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SonosSelectionForm from './SonosSelectionForm.svelte'
import { apiPut } from '../api.js'

vi.mock('../api.js', () => ({
  apiPut: vi.fn(),
}))

const speakers = [
  { uid: 'RINCON_1', name: 'Kitchen', host: '192.168.1.10', household_id: 'h', is_visible: true },
  { uid: 'RINCON_2', name: 'Living Room', host: '192.168.1.11', household_id: 'h', is_visible: true },
]

beforeEach(() => {
  apiPut.mockReset()
})

describe('SonosSelectionForm — prefill', () => {
  it('defaults to the first speaker when there is no saved selection', () => {
    render(SonosSelectionForm, { props: { speakers, selectedGroup: null, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByLabelText('Kitchen (192.168.1.10)')).toBeChecked()
    expect(screen.getByLabelText('Living Room (192.168.1.11)')).not.toBeChecked()
    expect(screen.getByLabelText('Coordinator')).toHaveValue('RINCON_1')
  })

  it('prefills members and coordinator from the saved selection', () => {
    const selectedGroup = { coordinator_uid: 'RINCON_2', members: [{ uid: 'RINCON_1' }, { uid: 'RINCON_2' }] }
    render(SonosSelectionForm, { props: { speakers, selectedGroup, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByLabelText('Kitchen (192.168.1.10)')).toBeChecked()
    expect(screen.getByLabelText('Living Room (192.168.1.11)')).toBeChecked()
    expect(screen.getByLabelText('Coordinator')).toHaveValue('RINCON_2')
  })
})

describe('SonosSelectionForm — submit', () => {
  it('toggles a speaker and submits the updated selection', async () => {
    apiPut.mockResolvedValue({})
    const onSaved = vi.fn()
    render(SonosSelectionForm, { props: { speakers, selectedGroup: null, onSaved, onCancel: vi.fn() } })

    await fireEvent.click(screen.getByLabelText('Living Room (192.168.1.11)'))
    await fireEvent.change(screen.getByLabelText('Coordinator'), { target: { value: 'RINCON_2' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPut).toHaveBeenCalledWith('/sonos/selection', {
      uids: ['RINCON_1', 'RINCON_2'],
      coordinator_uid: 'RINCON_2',
    })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled())
  })

  it('shows the API error and does not call onSaved', async () => {
    apiPut.mockRejectedValue({ body: { detail: 'Coordinator must be one of the selected speakers.' } })
    const onSaved = vi.fn()
    render(SonosSelectionForm, { props: { speakers, selectedGroup: null, onSaved, onCancel: vi.fn() } })

    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Coordinator must be one of the selected speakers.')).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('calls onCancel', async () => {
    const onCancel = vi.fn()
    render(SonosSelectionForm, { props: { speakers, selectedGroup: null, onSaved: vi.fn(), onCancel } })

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalled()
  })
})
