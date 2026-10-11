<script>
  // Floating console showing what is on the NFC reader — never what is playing: the admin process
  // has no playback state, and playback stays a physical gesture.
  import { tick } from 'svelte'
  import { typeIcon, typeLabel } from '../library/discType.js'

  // currentTag: null (nothing on the reader) | { tag_id, known_in_library }
  // disc: the library entry for a known tag, if already loaded
  let { currentTag = null, disc = undefined, actionsEnabled = true, onAdd, onEdit } = $props()

  const state = $derived(!currentTag ? 'empty' : currentTag.known_in_library ? 'known' : 'unknown')
  const status = $derived({ empty: 'No disc detected', unknown: 'Unknown disc', known: 'Disc detected' }[state])
  const title = $derived(
    {
      empty: 'Place a disc on the reader',
      unknown: 'New disc…',
      known: disc?.display_title ?? currentTag?.tag_id,
    }[state],
  )
  // No Edit without the library entry: it would open an empty edit form.
  const action = $derived(actionsEnabled ? { unknown: 'add', known: disc ? 'edit' : undefined }[state] : undefined)

  // Folded to a one-line bar on demand, so it stops covering the library on small screens. A reader
  // change never unfolds it (the status dot and text still update).
  let collapsed = $state(false)

  function setCollapsed(value) {
    collapsed = value
  }

  let collapseToggle = $state()
  let expandToggle = $state()

  // {#if} swaps the toggle buttons: hand keyboard focus over to the new one (gone if unmounted).
  function toggle(value) {
    setCollapsed(value)
    tick().then(() => (value ? expandToggle : collapseToggle)?.focus())
  }
</script>

<section class="reader-slot reader-slot-{state}" class:reader-slot-collapsed={collapsed} aria-label="Reader">
  <!-- Announces reader changes only, in both states: a live region on the whole widget would read
       it all again on each toggle. -->
  <p class="visually-hidden" role="status">{status} — {title}</p>

  {#if collapsed}
    <button class="expand-bar" aria-expanded="false" bind:this={expandToggle} onclick={() => toggle(false)}>
      <span class="visually-hidden">Expand reader:</span>
      <span class="status"><span class="status-dot" aria-hidden="true"></span>{status}</span>
      {#if state !== 'empty'}
        <span class="title">{title}</span>
      {/if}
      <span class="chevron" aria-hidden="true">▴</span>
    </button>
  {:else}
    <button
      class="collapse-toggle"
      aria-expanded="true"
      aria-label="Collapse reader"
      bind:this={collapseToggle}
      onclick={() => toggle(true)}
    >
      <span aria-hidden="true">▾</span>
    </button>

    <div class="disc-thumb">
      {#if state === 'known' && disc}
        <span class="emoji" role="img" aria-label={typeLabel(disc.display_type)}>{typeIcon(disc.display_type)}</span>
      {:else if state === 'unknown'}
        <span class="emoji emoji-unknown" aria-hidden="true">?</span>
      {:else}
        <span class="emoji emoji-empty" aria-hidden="true">💿</span>
      {/if}
    </div>

    <div class="reader-info">
      <span class="status"><span class="status-dot" aria-hidden="true"></span>{status}</span>
      <span class="field">
        <span class="field-label">Tag</span><code>{currentTag?.tag_id ?? '—'}</code>
      </span>
      <span class="field" title={disc?.uri}>
        <span class="field-label">URI</span><code>{disc?.uri ?? '—'}</code>
      </span>
    </div>

    <strong class="title">{title}</strong>

    {#if action === 'add'}
      <div class="reader-slot-action">
        <button class="pill" onclick={() => onAdd?.(currentTag.tag_id)}>
          <span aria-hidden="true">+</span> Add this disc
        </button>
      </div>
    {:else if action === 'edit'}
      <div class="reader-slot-action">
        <button class="pill" onclick={() => onEdit?.(currentTag.tag_id)}>
          <span aria-hidden="true">✎</span> Edit
        </button>
      </div>
    {/if}
  {/if}
</section>

<style>
  /* The console is fixed over the page: reserve its room inside #app, which holds the footer and
     the full-height min-height, so the footer sits right above the console. A body padding would
     come after a full-height #app: the footer would hide under the console and every page scroll. */
  :global(#app:has(.reader-slot)) {
    box-sizing: border-box;
  }

  :global(#app:has(.reader-slot:not(.reader-slot-collapsed))) {
    padding-bottom: 140px;
  }

  /* Collapsed bar: 44px tall with its borders, plus the same 16px below and above it as the full
     console. */
  :global(#app:has(.reader-slot-collapsed)) {
    padding-bottom: 76px;
  }

  .reader-slot {
    --c: var(--border);
    position: fixed;
    bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    left: 50%;
    transform: translateX(-50%);
    z-index: 900;
    box-sizing: border-box;
    width: min(1100px, calc(100vw - 32px));
    display: grid;
    grid-template-columns: auto minmax(0, 15rem) minmax(0, 1fr) auto;
    align-items: center;
    gap: 20px;
    padding: 12px 24px 12px 12px;
    background: color-mix(in srgb, var(--surface-2) 90%, transparent);
    backdrop-filter: blur(16px);
    border: 1px solid var(--hairline);
    border-radius: 26px;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.2);
  }

  .collapse-toggle {
    position: absolute;
    top: 6px;
    right: 10px;
    padding: 0 8px;
    font-size: 0.9em;
    line-height: 1.6;
    color: var(--text);
    background: none;
    border: none;
    border-radius: 8px;
  }

  .collapse-toggle:hover {
    background: var(--surface);
  }

  /* Collapsed: same width and position, folded to one line; the whole bar is the expand button. */
  .reader-slot-collapsed {
    display: block;
    padding: 0;
    border-radius: 18px;
  }

  .expand-bar {
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    height: 42px; /* 44px with the section borders */
    padding: 0 18px;
    color: var(--text);
    background: none;
    border: none;
    border-radius: inherit;
    text-align: left;
  }

  .expand-bar .status {
    flex-shrink: 0;
  }

  .expand-bar .title {
    font-size: 1em;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
    white-space: nowrap;
  }

  .chevron {
    margin-left: auto;
    opacity: 0.6;
  }

  .reader-slot-known {
    --c: var(--state-known);
  }

  .reader-slot-unknown {
    --c: var(--state-unknown);
  }

  /* Disc thumbnail — type emoji until cover art exists (L9). */
  .disc-thumb {
    display: grid;
    place-items: center;
    width: 72px;
    aspect-ratio: 1;
    border-radius: 28%;
    border: 1px solid color-mix(in srgb, var(--c) 60%, transparent);
    background: color-mix(in srgb, var(--c) 18%, var(--bg));
  }

  .reader-slot-empty .disc-thumb {
    border-style: dashed;
    background: none;
  }

  .emoji {
    font-size: 1.8em;
    line-height: 1;
  }

  .emoji-unknown {
    font-weight: 700;
    color: var(--c);
  }

  .emoji-empty {
    opacity: 0.35;
    filter: grayscale(1);
  }

  /* Reader details — always three lines, so the console keeps its height across states. */
  .reader-info {
    display: flex;
    flex-direction: column;
    gap: 3px;
    min-width: 0;
  }

  .status {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8em;
    font-weight: 600;
    color: var(--c);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--c);
  }

  .reader-slot-empty .status {
    color: var(--text);
  }

  .reader-slot-empty .status-dot {
    background: var(--text);
    opacity: 0.5;
  }

  .field {
    display: flex;
    gap: 6px;
    min-width: 0;
    font-size: 0.82em;
  }

  .field-label {
    flex-shrink: 0;
    width: 3ch;
    font-size: 0.85em;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    opacity: 0.6;
  }

  .field code {
    font-family: var(--mono);
    font-size: 0.9em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .title {
    min-width: 0;
    font-size: 1.15em;
    font-weight: 600;
    color: var(--text-h);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pill {
    padding: 10px 22px;
    border-radius: 14px;
    font-weight: 600;
    white-space: nowrap;
    color: #fff;
    background: var(--c);
    border-color: var(--c);
  }

  @media (max-width: 900px) {
    .reader-slot {
      grid-template-columns: auto minmax(0, 12rem) minmax(0, 1fr) auto;
      gap: 14px;
    }
  }

  /* Phones: disc first (what is it?), reader details below, full-width action last. */
  @media (max-width: 640px) {
    :global(#app:has(.reader-slot:not(.reader-slot-collapsed))) {
      padding-bottom: 240px;
    }

    .reader-slot {
      grid-template-columns: auto minmax(0, 1fr);
      grid-template-areas:
        'thumb title'
        'reader reader'
        'action action';
      gap: 10px 12px;
      padding: 12px 16px;
    }

    .reader-slot-collapsed {
      padding: 0;
    }

    .disc-thumb {
      grid-area: thumb;
      width: 48px;
    }

    .emoji {
      font-size: 1.4em;
    }

    .title {
      grid-area: title;
    }

    /* Clear of the collapse toggle in the top-right corner. */
    .collapse-toggle ~ .title {
      padding-right: 28px;
    }

    .reader-info {
      grid-area: reader;
      padding-top: 8px;
      border-top: 1px solid var(--border);
    }

    .reader-slot-action {
      grid-area: action;
    }

    .pill {
      width: 100%;
    }
  }
</style>
