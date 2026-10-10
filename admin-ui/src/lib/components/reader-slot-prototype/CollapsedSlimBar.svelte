<script>
  // PROTOTYPE variant A — "Slim bar": the widget keeps its width and position, only its height
  // shrinks to one line. Least surprising: it reads as the same object, folded.
  import { readerView } from './readerState.js'

  let { currentTag, disc, onExpand } = $props()
  const view = $derived(readerView(currentTag, disc))
</script>

<section class="proto-slim proto-{view.state}" aria-label="Reader" aria-live="polite">
  <button aria-expanded="false" aria-label="Expand reader" onclick={onExpand}>
    <span class="dot" aria-hidden="true"></span>
    <span class="status">{view.status}</span>
    {#if view.state !== 'empty'}
      <span class="sep" aria-hidden="true">·</span>
      <span class="title">{view.title}</span>
    {/if}
    <span class="chevron" aria-hidden="true">▴</span>
  </button>
</section>

<style>
  :global(#app:has(.proto-slim)) {
    box-sizing: border-box;
    padding-bottom: 76px;
  }

  .proto-slim {
    --c: var(--text);
    position: fixed;
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    left: 50%;
    transform: translateX(-50%);
    z-index: 900;
    width: min(1100px, calc(100vw - 32px));
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
    width: 100%;
    height: 44px;
    padding: 0 18px;
    color: var(--text);
    background: color-mix(in srgb, var(--surface-2) 90%, transparent);
    backdrop-filter: blur(16px);
    border: 1px solid var(--hairline);
    border-radius: 18px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.16);
    font-weight: 500;
    text-align: left;
  }

  .dot {
    flex-shrink: 0;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--c);
  }

  .proto-empty .dot {
    opacity: 0.5;
  }

  .status {
    flex-shrink: 0;
    font-size: 0.85em;
    font-weight: 600;
    color: var(--c);
  }

  .title {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-h);
  }

  .chevron {
    margin-left: auto;
    opacity: 0.6;
  }
</style>
