import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SonosSelectionForm from './SonosSelectionForm.svelte'
import { apiPost, apiPut } from '../api.js'

vi.mock('../api.js', () => ({
  apiPost: vi.fn(),
  apiPut: vi.fn(),
}))

const speakers = [
  { uid: 'RINCON_1', name: 'Kitchen', host: '192.168.1.10', household_id: 'h', is_visible: true },
  { uid: 'RINCON_2', name: 'Living Room', host: '192.168.1.11', household_id: 'h', is_visible: true },
]

const clearDialog = () => screen.getByRole('dialog', { name: 'Clear the saved selection?' })

beforeEach(() => {
  apiPost.mockReset()
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
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledWith('save'))
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

describe('SonosSelectionForm — clear', () => {
  const selectedGroup = { coordinator_uid: 'RINCON_1', members: [{ uid: 'RINCON_1' }] }

  it('hides Clear saved selection when there is no saved selection', () => {
    render(SonosSelectionForm, { props: { speakers, selectedGroup: null, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.queryByRole('button', { name: 'Clear saved selection' })).toBeNull()
  })

  it('places Clear saved selection between Save and Cancel', () => {
    render(SonosSelectionForm, { props: { speakers, selectedGroup, onSaved: vi.fn(), onCancel: vi.fn() } })

    const names = screen.getAllByRole('button').map((button) => button.textContent)
    expect(names).toEqual(['Save', 'Clear saved selection', 'Cancel'])
    expect(screen.getByRole('button', { name: 'Clear saved selection' })).toHaveClass('btn-danger')
  })

  it('resets the saved selection once confirmed and calls onSaved with clear', async () => {
    apiPost.mockResolvedValue({})
    const onSaved = vi.fn()
    render(SonosSelectionForm, { props: { speakers, selectedGroup, onSaved, onCancel: vi.fn() } })

    await fireEvent.click(screen.getByRole('button', { name: 'Clear saved selection' }))
    expect(apiPost).not.toHaveBeenCalled()
    await fireEvent.click(within(clearDialog()).getByRole('button', { name: 'Clear selection' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(apiPut).not.toHaveBeenCalled()
    expect(apiPost).toHaveBeenCalledWith('/settings/reset', { path: 'jukebox.player.sonos.selected_group' })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalledWith('clear'))
  })

  it('keeps the saved selection when the clear is cancelled, and gives the focus back to Clear', async () => {
    const onSaved = vi.fn()
    render(SonosSelectionForm, { props: { speakers, selectedGroup, onSaved, onCancel: vi.fn() } })
    const clear = screen.getByRole('button', { name: 'Clear saved selection' })

    await fireEvent.click(clear)
    await fireEvent.click(within(clearDialog()).getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(apiPost).not.toHaveBeenCalled()
    expect(apiPut).not.toHaveBeenCalled()
    expect(onSaved).not.toHaveBeenCalled()
    expect(clear).toHaveFocus()
  })

  it('shows the API error and does not call onSaved when clearing fails', async () => {
    apiPost.mockRejectedValue({ body: { detail: 'Reset failed.' } })
    const onSaved = vi.fn()
    render(SonosSelectionForm, { props: { speakers, selectedGroup, onSaved, onCancel: vi.fn() } })

    await fireEvent.click(screen.getByRole('button', { name: 'Clear saved selection' }))
    await fireEvent.click(within(clearDialog()).getByRole('button', { name: 'Clear selection' }))

    expect(await screen.findByText('Reset failed.')).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })
})
