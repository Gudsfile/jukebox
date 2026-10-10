<script>
  // PROTOTYPE variant D — "Docked tab": no longer floating; a thin strip glued to the bottom edge of
  // the viewport, full width, with a drawer handle. Reads as a drawer you pull up.
  import { readerView } from './readerState.js'

  let { currentTag, disc, onExpand } = $props()
  const view = $derived(readerView(currentTag, disc))
</script>

<section class="proto-dock proto-{view.state}" aria-label="Reader" aria-live="polite">
  <button aria-expanded="false" aria-label="Expand reader" onclick={onExpand}>
    <span class="handle" aria-hidden="true"></span>
    <span class="line">
      <span class="dot" aria-hidden="true"></span>
      <span class="text">{view.state === 'known' ? view.title : view.status}</span>
    </span>
  </button>
</section>

<style>
  :global(#app:has(.proto-dock)) {
    box-sizing: border-box;
    padding-bottom: 52px;
  }

  .proto-dock {
    --c: var(--text);
    position: fixed;
    inset: auto 0 0 0;
    z-index: 900;
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
    flex-direction: column;
    align-items: center;
    gap: 4px;
    width: 100%;
    padding: 6px 16px calc(8px + env(safe-area-inset-bottom, 0px));
    color: var(--text-h);
    background: color-mix(in srgb, var(--surface-2) 92%, transparent);
    backdrop-filter: blur(16px);
    border: none;
    border-top: 2px solid var(--c);
    border-radius: 16px 16px 0 0;
    box-shadow: 0 -8px 24px rgba(0, 0, 0, 0.12);
    font-weight: 500;
  }

  .proto-empty button {
    border-top-color: var(--border);
  }

  .handle {
    width: 36px;
    height: 4px;
    border-radius: 2px;
    background: var(--text);
    opacity: 0.35;
  }

  .line {
    display: flex;
    align-items: center;
    gap: 8px;
    max-width: 100%;
    font-size: 0.9em;
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

  .text {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
</style>
