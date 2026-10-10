<script>
  // PROTOTYPE variant B — "Pill": a compact, centered capsule sized to its content (like a
  // "now on the reader" island). Frees the bottom corners; the title is the main information.
  import { readerView } from './readerState.js'

  let { currentTag, disc, onExpand } = $props()
  const view = $derived(readerView(currentTag, disc))
</script>

<section class="proto-pill proto-{view.state}" aria-label="Reader" aria-live="polite">
  <button aria-expanded="false" aria-label="Expand reader: {view.status}" onclick={onExpand}>
    <span class="thumb" aria-hidden="true">{view.icon}</span>
    <span class="title">{view.state === 'known' ? view.title : view.status}</span>
    <span class="chevron" aria-hidden="true">▴</span>
  </button>
</section>

<style>
  :global(#app:has(.proto-pill)) {
    box-sizing: border-box;
    padding-bottom: 76px;
  }

  .proto-pill {
    --c: var(--border);
    position: fixed;
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    left: 50%;
    transform: translateX(-50%);
    z-index: 900;
    max-width: min(380px, calc(100vw - 32px));
  }

  .proto-known {
    --c: var(--state-known);
  }

  .proto-unknown {
    --c: var(--state-unknown);
  }

  button {
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 10px;
    max-width: 100%;
    padding: 5px 16px 5px 5px;
    color: var(--text-h);
    background: color-mix(in srgb, var(--surface-2) 90%, transparent);
    backdrop-filter: blur(16px);
    border: 1px solid var(--hairline);
    border-radius: 999px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    font-weight: 550;
  }

  .thumb {
    display: grid;
    place-items: center;
    flex-shrink: 0;
    width: 34px;
    aspect-ratio: 1;
    border-radius: 50%;
    border: 2px solid var(--c);
    background: color-mix(in srgb, var(--c) 18%, var(--bg));
    font-weight: 700;
    color: var(--c);
  }

  .proto-empty .thumb {
    border-style: dashed;
    background: none;
    filter: grayscale(1);
    opacity: 0.6;
  }

  .title {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .proto-unknown .title {
    color: var(--c);
  }

  .chevron {
    flex-shrink: 0;
    opacity: 0.6;
  }
</style>
