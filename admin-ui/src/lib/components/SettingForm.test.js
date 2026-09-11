import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SettingForm from './SettingForm.svelte'
import { apiPatch, apiPost } from '../api.js'

vi.mock('../api.js', () => ({
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
}))

function baseSetting(overrides = {}) {
  return {
    path: 'admin.api.port',
    label: 'Admin API Port',
    description: 'TCP port used by the admin API server.',
    field_type: 'integer',
    section: 'admin',
    section_label: 'Admin',
    choices: [],
    default_value: 8000,
    persisted_value: null,
    effective_value: 8000,
    provenance: 'default',
    is_persisted: false,
    ...overrides,
  }
}

beforeEach(() => {
  apiPatch.mockReset()
  apiPost.mockReset()
})

describe('SettingForm — field types', () => {
  it('integer: prefills from the effective value and PATCHes a coerced number', async () => {
    apiPatch.mockResolvedValue({})
    const onSaved = vi.fn()
    render(SettingForm, { props: { setting: baseSetting(), onSaved, onCancel: vi.fn() } })

    expect(screen.getByRole('spinbutton')).toHaveValue(8000)
    await fireEvent.input(screen.getByRole('spinbutton'), { target: { value: '9000' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPatch).toHaveBeenCalledWith('/settings', { admin: { api: { port: 9000 } } })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled())
  })

  it('integer: rejects a non-numeric value without calling apiPatch', async () => {
    render(SettingForm, { props: { setting: baseSetting(), onSaved: vi.fn(), onCancel: vi.fn() } })

    await fireEvent.input(screen.getByRole('spinbutton'), { target: { value: 'not-a-number' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Enter a valid integer.')).toBeInTheDocument()
    expect(apiPatch).not.toHaveBeenCalled()
  })

  it('number: coerces to a float', async () => {
    apiPatch.mockResolvedValue({})
    const setting = baseSetting({
      path: 'jukebox.playback.pause_delay_seconds',
      field_type: 'number',
      effective_value: 0.25,
    })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    await fireEvent.input(screen.getByRole('spinbutton'), { target: { value: '0.5' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPatch).toHaveBeenCalledWith('/settings', { jukebox: { playback: { pause_delay_seconds: 0.5 } } })
  })

  it('object: stringifies the initial value as JSON and parses it back on submit', async () => {
    apiPatch.mockResolvedValue({})
    const setting = baseSetting({
      path: 'jukebox.player.sonos.selected_group',
      field_type: 'object',
      effective_value: { coordinator_uid: 'a' },
    })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByRole('textbox')).toHaveValue(JSON.stringify({ coordinator_uid: 'a' }, null, 2))

    await fireEvent.input(screen.getByRole('textbox'), { target: { value: '{"coordinator_uid": "b"}' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPatch).toHaveBeenCalledWith('/settings', {
      jukebox: { player: { sonos: { selected_group: { coordinator_uid: 'b' } } } },
    })
  })

  it('object: blank input persists null', async () => {
    apiPatch.mockResolvedValue({})
    const setting = baseSetting({ path: 'jukebox.player.sonos.selected_group', field_type: 'object' })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    await fireEvent.input(screen.getByRole('textbox'), { target: { value: '' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPatch).toHaveBeenCalledWith('/settings', { jukebox: { player: { sonos: { selected_group: null } } } })
  })

  it('object: invalid JSON shows an error', async () => {
    const setting = baseSetting({ path: 'jukebox.player.sonos.selected_group', field_type: 'object' })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    await fireEvent.input(screen.getByRole('textbox'), { target: { value: '{not json' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Enter valid JSON.')).toBeInTheDocument()
    expect(apiPatch).not.toHaveBeenCalled()
  })

  it('choices: renders a select and submits the chosen value', async () => {
    apiPatch.mockResolvedValue({})
    const setting = baseSetting({
      path: 'jukebox.player.type',
      field_type: 'string',
      effective_value: 'dryrun',
      choices: [
        { value: 'dryrun', label: 'Dry Run' },
        { value: 'sonos', label: 'Sonos' },
      ],
    })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    await fireEvent.change(screen.getByRole('combobox'), { target: { value: 'sonos' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPatch).toHaveBeenCalledWith('/settings', { jukebox: { player: { type: 'sonos' } } })
  })
})

describe('SettingForm — reset and cancel', () => {
  it('shows Reset only when the setting is persisted, and posts the reset path', async () => {
    apiPost.mockResolvedValue({})
    const onSaved = vi.fn()
    render(SettingForm, {
      props: { setting: baseSetting({ is_persisted: true, persisted_value: 9000 }), onSaved, onCancel: vi.fn() },
    })

    await fireEvent.click(screen.getByRole('button', { name: 'Reset' }))

    expect(apiPost).toHaveBeenCalledWith('/settings/reset', { path: 'admin.api.port' })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled())
  })

  it('hides Reset when the setting has no persisted override', () => {
    render(SettingForm, {
      props: { setting: baseSetting({ is_persisted: false }), onSaved: vi.fn(), onCancel: vi.fn() },
    })

    expect(screen.queryByRole('button', { name: 'Reset' })).toBeNull()
  })

  it('calls onCancel', async () => {
    const onCancel = vi.fn()
    render(SettingForm, { props: { setting: baseSetting(), onSaved: vi.fn(), onCancel } })

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalled()
  })
})

describe('SettingForm — server errors', () => {
  it('shows the server error when saving fails and does not call onSaved', async () => {
    apiPatch.mockRejectedValue({ body: { detail: 'Enter a valid integer.' } })
    const onSaved = vi.fn()
    render(SettingForm, { props: { setting: baseSetting(), onSaved, onCancel: vi.fn() } })

    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Enter a valid integer.')).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('shows the server error when reset fails and does not call onSaved', async () => {
    apiPost.mockRejectedValue({ body: { detail: 'Settings file is corrupted.' } })
    const onSaved = vi.fn()
    render(SettingForm, {
      props: { setting: baseSetting({ is_persisted: true, persisted_value: 9000 }), onSaved, onCancel: vi.fn() },
    })

    await fireEvent.click(screen.getByRole('button', { name: 'Reset' }))

    expect(await screen.findByText('Settings file is corrupted.')).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })
})
