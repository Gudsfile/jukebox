import { render, screen } from '@testing-library/svelte'
import { fireEvent } from '@testing-library/dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DiscForm from './DiscForm.svelte'
import { ApiError, apiPatch, apiPost } from '../api.js'

vi.mock('../api.js', () => ({
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(status, body) {
      super(`API error ${status}`)
      this.status = status
      this.body = body
    }
  },
}))

beforeEach(() => {
  apiPost.mockReset()
  apiPatch.mockReset()
})

describe('DiscForm — create mode', () => {
  it('starts with the given prefill tag and empty fields', () => {
    render(DiscForm, { props: { mode: 'create', tagId: 'tag-abc', onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByLabelText('Tag ID')).toHaveValue('tag-abc')
    expect(screen.getByLabelText('Tag ID')).toBeEnabled()
    expect(screen.getByLabelText('URI / Path')).toHaveValue('')
  })

  it('submits a POST with the full disc payload and calls onSaved', async () => {
    apiPost.mockResolvedValue({})
    const onSaved = vi.fn()
    render(DiscForm, { props: { mode: 'create', tagId: 'tag-abc', onSaved, onCancel: vi.fn() } })

    await fireEvent.input(screen.getByLabelText('URI / Path'), { target: { value: '/music/song.mp3' } })
    await fireEvent.input(screen.getByLabelText('Artist'), { target: { value: 'Some Artist' } })
    await fireEvent.click(screen.getByLabelText('Shuffle'))
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPost).toHaveBeenCalledWith('/discs/tag-abc', {
      uri: '/music/song.mp3',
      metadata: { artist: 'Some Artist', album: '', track: '', playlist: '' },
      option: { shuffle: true },
    })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled())
  })
})

describe('DiscForm — edit mode', () => {
  const disc = {
    uri: '/music/song.mp3',
    metadata: { artist: 'Artist', album: 'Album', track: 'Track', playlist: null },
    option: { shuffle: true },
  }

  it('prefills from the disc prop and disables the tag field', () => {
    render(DiscForm, { props: { mode: 'edit', tagId: 'tag-abc', disc, onSaved: vi.fn(), onCancel: vi.fn() } })

    expect(screen.getByLabelText('Tag ID')).toHaveValue('tag-abc')
    expect(screen.getByLabelText('Tag ID')).toBeDisabled()
    expect(screen.getByLabelText('Artist')).toHaveValue('Artist')
    expect(screen.getByLabelText('Shuffle')).toBeChecked()
  })

  it('submits a PATCH to the existing tag', async () => {
    apiPatch.mockResolvedValue({})
    const onSaved = vi.fn()
    render(DiscForm, { props: { mode: 'edit', tagId: 'tag-abc', disc, onSaved, onCancel: vi.fn() } })

    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(apiPatch).toHaveBeenCalledWith('/discs/tag-abc', {
      uri: '/music/song.mp3',
      // playlist round-trips as '' — text inputs can't hold null, so the empty prefill sticks.
      metadata: { artist: 'Artist', album: 'Album', track: 'Track', playlist: '' },
      option: { shuffle: true },
    })
    await vi.waitFor(() => expect(onSaved).toHaveBeenCalled())
  })
})

describe('DiscForm — errors and cancel', () => {
  it('shows the API error detail and does not call onSaved', async () => {
    apiPost.mockRejectedValue(new ApiError(409, { detail: 'Tag already exists' }))
    const onSaved = vi.fn()
    render(DiscForm, { props: { mode: 'create', tagId: 'tag-abc', onSaved, onCancel: vi.fn() } })

    await fireEvent.input(screen.getByLabelText('URI / Path'), { target: { value: '/music/song.mp3' } })
    await fireEvent.click(screen.getByRole('button', { name: 'Save' }))

    expect(await screen.findByText('Tag already exists')).toBeInTheDocument()
    expect(onSaved).not.toHaveBeenCalled()
  })

  it('calls onCancel when Cancel is clicked', async () => {
    const onCancel = vi.fn()
    render(DiscForm, { props: { mode: 'create', tagId: '', onSaved: vi.fn(), onCancel } })

    await fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))

    expect(onCancel).toHaveBeenCalled()
  })
})
