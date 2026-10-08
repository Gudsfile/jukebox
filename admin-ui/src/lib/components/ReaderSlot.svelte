<script>
  // Floating console showing what is on the NFC reader — never what is playing: the admin process
  // has no playback state, and playback stays a physical gesture.
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
</script>

<section class="reader-slot reader-slot-{state}" aria-label="Reader" aria-live="polite">
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
</section>

<style>
  /* The console is fixed over the page: reserve room so the end of the page (footer included)
     can still be scrolled into view above it. */
  :global(body:has(.reader-slot)) {
    padding-bottom: 140px;
  }

  .reader-slot {
    --c: var(--border);
    --c-bg: transparent;
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
    background: linear-gradient(90deg, var(--c-bg), transparent 70%), color-mix(in srgb, var(--bg) 88%, transparent);
    backdrop-filter: blur(12px);
    border: 1.5px solid color-mix(in srgb, var(--c) 70%, transparent);
    border-radius: 999px;
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.16);
    transition: border-color 0.3s;
  }

  .reader-slot-known {
    --c: var(--state-known);
    --c-bg: var(--state-known-bg);
  }

  .reader-slot-unknown {
    --c: var(--state-unknown);
    --c-bg: var(--state-unknown-bg);
  }

  /* Disc thumbnail — type emoji until cover art exists (L9). */
  .disc-thumb {
    display: grid;
    place-items: center;
    width: 72px;
    aspect-ratio: 1;
    border-radius: 50%;
    border: 2px solid color-mix(in srgb, var(--c) 60%, transparent);
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
    border-radius: 999px;
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
    :global(body:has(.reader-slot)) {
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
      border-radius: 24px;
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
