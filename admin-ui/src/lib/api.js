const BASE_URL = '/api/v1'

class ApiError extends Error {
  constructor(status, body) {
    super(`API error ${status}`)
    this.status = status
    this.body = body
  }
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => null))
  }
  if (res.status === 204) return null
  return res.json()
}

export function apiGet(path) {
  return request(path)
}

export function apiPost(path, body) {
  return request(path, { method: 'POST', body: JSON.stringify(body) })
}

export function apiPut(path, body) {
  return request(path, { method: 'PUT', body: JSON.stringify(body) })
}

export function apiPatch(path, body) {
  return request(path, { method: 'PATCH', body: JSON.stringify(body) })
}

export function apiDelete(path) {
  return request(path, { method: 'DELETE' })
}

export async function apiDownload(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) {
    throw new ApiError(res.status, await res.json().catch(() => null))
  }
  const disposition = res.headers.get('Content-Disposition') ?? ''
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] ?? `${path.split('/').at(-1)}.json`
  return { blob: await res.blob(), filename }
}

export { ApiError, BASE_URL }
