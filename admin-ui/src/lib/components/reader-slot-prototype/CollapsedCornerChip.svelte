<script>
  // PROTOTYPE variant C — "Corner chip": the widget shrinks to a round button in the bottom-right
  // corner, like a floating action button. Smallest footprint; the state is told by color and
  // icon only, the text lives in the tooltip and the accessible name.
  import { readerView } from './readerState.js'

  let { currentTag, disc, onExpand } = $props()
  const view = $derived(readerView(currentTag, disc))
</script>

<section class="proto-chip proto-{view.state}" aria-label="Reader" aria-live="polite">
  <button
    aria-expanded="false"
    aria-label="Expand reader: {view.status}, {view.title}"
    title="{view.status} — {view.title}"
    onclick={onExpand}
  >
    <span class="icon" aria-hidden="true">{view.icon}</span>
    <span class="badge" aria-hidden="true"></span>
  </button>
</section>

<style>
  /* The chip sits in a corner: no page room reserved, it only covers the end of the last row. */
  .proto-chip {
    --c: var(--border);
    position: fixed;
    right: calc(16px + env(safe-area-inset-right, 0px));
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    z-index: 900;
  }

  .proto-known {
    --c: var(--state-known);
  }

  .proto-unknown {
    --c: var(--state-unknown);
  }

  button {
    position: relative;
    display: grid;
    place-items: center;
    width: 58px;
    aspect-ratio: 1;
    padding: 0;
    color: var(--c);
    background: color-mix(in srgb, var(--c) 18%, var(--surface-2));
    backdrop-filter: blur(16px);
    border: 2px solid var(--c);
    border-radius: 50%;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.22);
  }

  .proto-empty button {
    border-style: dashed;
    background: color-mix(in srgb, var(--surface-2) 90%, transparent);
  }

  .icon {
    font-size: 1.5em;
    font-weight: 700;
    line-height: 1;
  }

  .proto-empty .icon {
    filter: grayscale(1);
    opacity: 0.4;
  }

  .badge {
    position: absolute;
    top: 2px;
    right: 2px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--c);
    border: 2px solid var(--bg);
  }

  .proto-empty .badge {
    display: none;
  }
</style>
