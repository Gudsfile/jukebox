import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiDelete, apiDownload, apiGet, apiPatch, apiPost, apiPut, apiUpload } from './api.js'

function mockFetchOnce({ ok = true, status = 200, body = {} } = {}) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
  })
}

beforeEach(() => {
  globalThis.fetch = vi.fn()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('apiGet', () => {
  it('requests the given path under /api/v1', async () => {
    mockFetchOnce({ body: { hello: 'world' } })

    const result = await apiGet('/discs')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/discs',
      expect.objectContaining({ headers: expect.objectContaining({ 'Content-Type': 'application/json' }) }),
    )
    expect(result).toEqual({ hello: 'world' })
  })
})

describe('apiPost / apiPut / apiPatch', () => {
  it.each([
    ['apiPost', apiPost, 'POST'],
    ['apiPut', apiPut, 'PUT'],
    ['apiPatch', apiPatch, 'PATCH'],
  ])('%s sends the method and JSON body', async (_name, fn, method) => {
    mockFetchOnce({ body: { saved: true } })

    const result = await fn('/settings', { value: 42 })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/settings',
      expect.objectContaining({ method, body: JSON.stringify({ value: 42 }) }),
    )
    expect(result).toEqual({ saved: true })
  })
})

describe('apiDelete', () => {
  it('sends a DELETE request', async () => {
    mockFetchOnce({ ok: true, status: 204, body: null })

    const result = await apiDelete('/discs/tag-123')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/discs/tag-123',
      expect.objectContaining({ method: 'DELETE' }),
    )
    expect(result).toBeNull()
  })
})

describe('error handling', () => {
  it('throws ApiError with the status and parsed body on a non-ok response', async () => {
    mockFetchOnce({ ok: false, status: 409, body: { detail: 'Tag already exists' } })

    await expect(apiPost('/discs/tag-123', {})).rejects.toMatchObject(
      new ApiError(409, { detail: 'Tag already exists' }),
    )
  })

  it('falls back to a null body when the error response has no JSON', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.reject(new Error('not json')),
    })

    const error = await apiGet('/discs').catch((err) => err)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(500)
    expect(error.body).toBeNull()
  })

  it('returns null for a 204 No Content success response', async () => {
    mockFetchOnce({ ok: true, status: 204, body: null })

    const result = await apiGet('/settings/reset')

    expect(result).toBeNull()
  })
})

describe('apiUpload', () => {
  it('posts the file as is and returns the parsed response', async () => {
    mockFetchOnce({ body: { disc_count: 1 } })
    const file = new File(['{"discs": {}}'], 'library.json', { type: 'application/json' })

    const result = await apiUpload('/import/library', file)

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/import/library',
      expect.objectContaining({ method: 'POST', body: file }),
    )
    expect(result).toEqual({ disc_count: 1 })
  })

  it('passes extra fetch options such as an abort signal', async () => {
    mockFetchOnce()
    const { signal } = new AbortController()

    await apiUpload('/import/library/preview', new File(['{}'], 'library.json'), { signal })

    expect(globalThis.fetch).toHaveBeenCalledWith(
      '/api/v1/import/library/preview',
      expect.objectContaining({ method: 'POST', signal }),
    )
  })

  it('throws an ApiError carrying the response body', async () => {
    mockFetchOnce({ ok: false, status: 400, body: { detail: 'Invalid library file' } })

    await expect(apiUpload('/import/library', new File([''], 'library.json'))).rejects.toMatchObject({
      status: 400,
      body: { detail: 'Invalid library file' },
    })
  })
})

describe('apiDownload', () => {
  function mockDownloadOnce({ ok = true, status = 200, disposition = null, body = null } = {}) {
    const blob = new Blob(['{}'], { type: 'application/json' })
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok,
      status,
      headers: new Headers(disposition ? { 'Content-Disposition': disposition } : {}),
      blob: () => Promise.resolve(blob),
      json: () => Promise.resolve(body),
    })
    return blob
  }

  it('returns the file content and the file name given by the server', async () => {
    const blob = mockDownloadOnce({ disposition: 'attachment; filename="library-2026-11-11.json"' })

    const result = await apiDownload('/export/library')

    expect(globalThis.fetch).toHaveBeenCalledWith('/api/v1/export/library')
    expect(result).toEqual({ blob, filename: 'library-2026-11-11.json' })
  })

  it('falls back to the last path segment when the server gives no file name', async () => {
    mockDownloadOnce()

    const result = await apiDownload('/export/settings')

    expect(result.filename).toBe('settings.json')
  })

  it('throws an ApiError carrying the error body instead of returning it as a file', async () => {
    mockDownloadOnce({ ok: false, status: 404, body: { detail: 'No library file to export.' } })

    const error = await apiDownload('/export/library').catch((err) => err)

    expect(error).toBeInstanceOf(ApiError)
    expect(error.status).toBe(404)
    expect(error.body).toEqual({ detail: 'No library file to export.' })
  })
})
