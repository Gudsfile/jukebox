<script>
  let { onEditDisc, onAddDisc } = $props()

  let currentTag = $state(null)

  $effect(() => {
    // EventSource reconnects automatically on connection drop — no custom retry logic needed.
    const source = new EventSource('/api/v1/current-tag/events')
    source.onmessage = (event) => {
      currentTag = JSON.parse(event.data)
    }
    return () => source.close()
  })
</script>

{#if currentTag}
  <div class="banner" class:banner-info={currentTag.known_in_library} class:banner-warning={!currentTag.known_in_library}>
    <div>
      <h4>{currentTag.known_in_library ? 'Known disc on reader' : 'Unknown disc on reader'}</h4>
      <p>
        Tag "{currentTag.tag_id}" is
        {currentTag.known_in_library ? 'already in the library.' : 'ready to be added to the library.'}
      </p>
    </div>
    {#if currentTag.known_in_library}
      <button onclick={() => onEditDisc?.(currentTag.tag_id)}>Edit this disc</button>
    {:else}
      <button onclick={() => onAddDisc?.(currentTag.tag_id)}>Add this disc</button>
    {/if}
  </div>
{/if}
