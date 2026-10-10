<script>
  // PROTOTYPE, throwaway: variant switcher. Pinned top-right, not bottom-centre: the bottom of the
  // screen is the very spot being evaluated. ← / → cycle variants (ignored while typing).
  let { variants, current, onChange, readerStates, readerState = $bindable(), collapsed = $bindable() } = $props()

  const keys = $derived(Object.keys(variants))

  function cycle(step) {
    const index = keys.indexOf(current)
    onChange(keys[(index + step + keys.length) % keys.length])
  }

  function onKeydown(event) {
    const target = event.target
    if (target.closest?.('input, textarea, select, [contenteditable]')) return
    if (event.key === 'ArrowLeft') cycle(-1)
    if (event.key === 'ArrowRight') cycle(1)
  }
</script>

<svelte:window onkeydown={onKeydown} />

<aside class="proto-switcher" aria-label="Prototype switcher">
  <div class="row">
    <button onclick={() => cycle(-1)} aria-label="Previous variant">←</button>
    <strong>{current} ({variants[current]})</strong>
    <button onclick={() => cycle(1)} aria-label="Next variant">→</button>
  </div>
  <div class="row">
    {#each readerStates as key (key)}
      <button class:active={readerState === key} onclick={() => (readerState = key)}>{key}</button>
    {/each}
  </div>
  <div class="row">
    <button onclick={() => (collapsed = !collapsed)}>{collapsed ? 'Expand' : 'Collapse'}</button>
    <code>variant={current} · collapsed={collapsed} · reader={readerState}</code>
  </div>
</aside>

<style>
  .proto-switcher {
    position: fixed;
    top: 12px;
    right: 12px;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    gap: 6px;
    max-width: calc(100vw - 24px);
    padding: 8px 10px;
    font: 12px/1.4 var(--mono);
    color: #fff;
    background: #e0007a;
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  }

  .row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
  }

  button {
    padding: 2px 8px;
    font: inherit;
    color: #fff;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.4);
    border-radius: 6px;
  }

  button.active {
    color: #e0007a;
    background: #fff;
  }
</style>
