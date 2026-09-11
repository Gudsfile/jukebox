import { svelte } from '@sveltejs/vite-plugin-svelte'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  base: '/ui/',
  plugins: [svelte()],
  test: {
    environment: 'jsdom',
    // Flags timers/sockets/watchers left running after a test finishes (e.g. an unclosed
    // EventSource), which would otherwise leak into and pollute later tests.
    setupFiles: ['./vitest-setup.js', 'vitest-leak-detector/setup'],
    reporters: ['default', 'vitest-leak-detector/reporter'],
  },
  // Under Vitest, force the browser build of Svelte (and any package with separate
  // server/browser exports) — otherwise component mounting picks the server build and throws
  // "mount(...) is not available on the server".
  resolve: process.env.VITEST ? { conditions: ['browser'] } : undefined,
})
