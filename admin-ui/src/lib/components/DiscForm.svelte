<script>
  import { untrack } from 'svelte'
  import { apiPatch, apiPost } from '../api.js'

  let { mode, tagId: initialTagId = '', disc = null, onSaved, onCancel } = $props()

  // Prefill from props once at mount — Library.svelte always remounts this component
  // (different {#if} branch) rather than updating `disc` in place, so a one-time read is correct.
  let tagId = $state(untrack(() => initialTagId))
  let uri = $state(untrack(() => disc?.uri ?? ''))
  let artist = $state(untrack(() => disc?.metadata.artist ?? ''))
  let album = $state(untrack(() => disc?.metadata.album ?? ''))
  let track = $state(untrack(() => disc?.metadata.track ?? ''))
  let playlist = $state(untrack(() => disc?.metadata.playlist ?? ''))
  let shuffle = $state(untrack(() => disc?.option.shuffle ?? false))
  let error = $state(null)
  let saving = $state(false)

  async function handleSubmit(event) {
    event.preventDefault()
    saving = true
    error = null

    const payload = {
      uri,
      metadata: { artist, album, track, playlist },
      option: { shuffle },
    }

    try {
      if (mode === 'create') {
        await apiPost(`/discs/${tagId}`, payload)
      } else {
        await apiPatch(`/discs/${tagId}`, payload)
      }
      onSaved()
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      saving = false
    }
  }
</script>

<form onsubmit={handleSubmit}>
  <label>
    Tag ID
    <input bind:value={tagId} disabled={mode === 'edit'} required />
  </label>
  <label>
    URI / Path
    <input bind:value={uri} required />
  </label>
  <label>
    Artist
    <input bind:value={artist} />
  </label>
  <label>
    Album
    <input bind:value={album} />
  </label>
  <label>
    Track
    <input bind:value={track} />
  </label>
  <label>
    Playlist
    <input bind:value={playlist} />
  </label>
  <label class="checkbox">
    <input type="checkbox" bind:checked={shuffle} />
    Shuffle
  </label>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div class="actions">
    <button type="submit" class="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
    <button type="button" class="btn-secondary" onclick={onCancel}>Cancel</button>
  </div>
</form>
