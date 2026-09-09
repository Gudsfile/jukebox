import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/svelte'

afterEach(() => cleanup())

// jsdom has no EventSource implementation — CurrentTagBanner (and anything
// that mounts it, e.g. App) needs a stub so component tests don't throw.
if (!globalThis.EventSource) {
  globalThis.EventSource = class EventSource {
    constructor(url) {
      this.url = url
      this.onmessage = null
    }
    close() {}
  }
}
