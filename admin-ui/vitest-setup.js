import { afterEach } from 'vitest'
import { cleanup } from '@testing-library/svelte'
import '@testing-library/jest-dom/vitest'
import { toastStore } from './src/lib/stores/toastStore.js'

afterEach(() => cleanup())

// The toast store is a module singleton: a toast shown by a test leaves its auto-dismiss
// timer running past the test, so clear it.
afterEach(() => toastStore.dismiss())

// jsdom has no EventSource implementation — the Library page (and anything that mounts
// it, e.g. App) needs a stub so component tests don't throw. Instances are tracked so tests can
// grab the latest one and call `.onmessage({ data })` to simulate a server push.
if (!globalThis.EventSource) {
  class FakeEventSource {
    constructor(url) {
      this.url = url
      this.onmessage = null
      FakeEventSource.instances.push(this)
    }
    close() {}
  }
  FakeEventSource.instances = []
  globalThis.EventSource = FakeEventSource
}

afterEach(() => {
  globalThis.EventSource.instances.length = 0
})
