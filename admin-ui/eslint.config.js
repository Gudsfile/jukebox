import svelteConfig from './svelte.config.js'
import { defineConfig } from 'eslint/config'
import globals from 'globals'
import js from '@eslint/js'
import svelte from 'eslint-plugin-svelte'

export default defineConfig([
  { ignores: ['dist/**'] },
  js.configs.recommended,
  svelte.configs.recommended,
  svelte.configs.prettier,
  {
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
  },
  {
    files: ['**/*.svelte', '**/*.svelte.js'],
    languageOptions: {
      parserOptions: {
        svelteConfig,
      },
    },
  },
  {
    rules: {
      // We reassign a new Set on each update ($state already tracks the reassignment), so
      // SvelteSet's in-place mutation reactivity isn't needed here.
      'svelte/prefer-svelte-reactivity': 'off',
    },
  },
])
