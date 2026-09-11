import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiDelete, apiGet, apiPatch, apiPost, apiPut } from './api.js'

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
