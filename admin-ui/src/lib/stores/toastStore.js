import { writable } from 'svelte/store'

const DISMISS_TIMEOUT_MS = 3000

function createToastStore() {
  const { subscribe, set } = writable(null)
  let currentTimeoutId = null

  return {
    subscribe,
    showToast: (message) => {
      if (currentTimeoutId !== null) {
        clearTimeout(currentTimeoutId)
      }

      set({ message })

      currentTimeoutId = setTimeout(() => {
        set(null)
        currentTimeoutId = null
      }, DISMISS_TIMEOUT_MS)

      return () => {
        clearTimeout(currentTimeoutId)
        currentTimeoutId = null
      }
    },
    dismiss: () => {
      if (currentTimeoutId !== null) {
        clearTimeout(currentTimeoutId)
        currentTimeoutId = null
      }
      set(null)
    },
  }
}

export { createToastStore }
export const toastStore = createToastStore()
