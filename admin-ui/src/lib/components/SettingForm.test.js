import { render, screen, within } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import SettingForm from './SettingForm.svelte'
import { apiPatch, apiPost } from '../api.js'

vi.mock('../api.js', () => ({
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
}))

const resetDialog = () => screen.getByRole('dialog', { name: 'Reset Admin API Port?' })

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
  it('shows Reset only when the setting is persisted, and posts the reset path once confirmed', async () => {
    apiPost.mockResolvedValue({})
    const onSaved = vi.fn()
    render(SettingForm, {
      props: { setting: baseSetting({ is_persisted: true, persisted_value: 9000 }), onSaved, onCancel: vi.fn() },
    })

    await fireEvent.click(screen.getByRole('button', { name: 'Reset' }))
    expect(apiPost).not.toHaveBeenCalled()
    await fireEvent.click(within(resetDialog()).getByRole('button', { name: 'Reset' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(apiPost).toHaveBeenCalledWith('/settings/reset', { path: 'admin.api.port' })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled())
  })

  it('keeps the persisted override when the reset is cancelled, and gives the focus back to Reset', async () => {
    const onSaved = vi.fn()
    render(SettingForm, {
      props: { setting: baseSetting({ is_persisted: true, persisted_value: 9000 }), onSaved, onCancel: vi.fn() },
    })
    const reset = screen.getByRole('button', { name: 'Reset' })

    await fireEvent.click(reset)
    await fireEvent.click(within(resetDialog()).getByRole('button', { name: 'Cancel' }))

    expect(screen.queryByRole('dialog')).toBeNull()
    expect(apiPost).not.toHaveBeenCalled()
    expect(onSaved).not.toHaveBeenCalled()
    expect(reset).toHaveFocus()
  })

  it('hides Reset when the setting has no persisted override', () => {
    render(SettingForm, {
      props: { setting: baseSetting({ is_persisted: false }), onSaved: vi.fn(), onCancel: vi.fn() },
    })

    expect(screen.queryByRole('button', { name: 'Reset' })).toBeNull()
  })

  it('explains that environment and CLI overrides can supersede the saved value', () => {
    render(SettingForm, { props: { setting: baseSetting(), onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByText(/may still be superseded by environment or CLI overrides/)).toBeInTheDocument()
    expect(screen.queryByText(/Reset removes the persisted override/)).toBeNull()
  })

  it('explains what Reset falls back to when the setting is persisted', () => {
    render(SettingForm, {
      props: {
        setting: baseSetting({ is_persisted: true, persisted_value: 9000 }),
        onSaved: vi.fn(),
        onCancel: vi.fn(),
      },
    })

    expect(screen.getByText(/Reset removes the persisted override/)).toBeInTheDocument()
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
    await fireEvent.click(within(resetDialog()).getByRole('button', { name: 'Reset' }))

    expect(await screen.findByText('Settings file is corrupted.')).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })
})

describe('SettingForm — current values', () => {
  function currentValues() {
    const region = screen.getByRole('region', { name: 'Current values' })
    const values = {}
    for (const term of region.querySelectorAll('dt')) {
      values[term.textContent] = term.nextElementSibling.textContent.trim()
    }
    return values
  }

  it('shows the default, effective value and source, and a dash when not persisted', () => {
    render(SettingForm, { props: { setting: baseSetting(), onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(currentValues()).toEqual({
      Default: '8000',
      Persisted: '—',
      'Effective value': '8000',
      Source: 'Default',
    })
  })

  it('shows the persisted override read from the settings file', () => {
    const setting = baseSetting({
      is_persisted: true,
      persisted_value: 9000,
      effective_value: 9000,
      provenance: 'file',
    })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(currentValues()).toEqual({
      Default: '8000',
      Persisted: '9000',
      'Effective value': '9000',
      Source: 'Settings file',
    })
  })

  it('shows an environment-sourced effective value that differs from the persisted one', () => {
    const setting = baseSetting({ is_persisted: true, persisted_value: 9000, effective_value: 7000, provenance: 'env' })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(currentValues()).toEqual({
      Default: '8000',
      Persisted: '9000',
      'Effective value': '7000',
      Source: 'Environment override',
    })
  })

  it('shows the section label and the same badges as the Settings table', () => {
    const setting = baseSetting({
      is_persisted: true,
      persisted_value: 9000,
      is_pinned_default: true,
      requires_restart: true,
      advanced: true,
    })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    const section = screen.getByText(/Admin setting/)
    expect(within(section).getByText('Configured')).toBeInTheDocument()
    expect(within(section).getByText('Pinned default')).toBeInTheDocument()
    expect(within(section).getByText('Restart required')).toBeInTheDocument()
    expect(within(section).getByText('Advanced')).toBeInTheDocument()
  })

  it('lets the keyboard reach the object values, which may scroll, and only them', () => {
    const group = { coordinator_uid: 'RINCON_1' }
    const setting = baseSetting({
      field_type: 'object',
      default_value: null,
      is_persisted: true,
      persisted_value: group,
      effective_value: group,
    })
    render(SettingForm, { props: { setting, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByRole('group', { name: 'Persisted' })).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('group', { name: 'Effective value' })).toHaveAttribute('tabindex', '0')
    expect(screen.queryByRole('group', { name: 'Default' })).not.toBeInTheDocument()
  })

  it('shows no badges for a plain default setting', () => {
    render(SettingForm, { props: { setting: baseSetting(), onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByText(/Admin setting/).querySelectorAll('.badge')).toHaveLength(0)
  })
})
