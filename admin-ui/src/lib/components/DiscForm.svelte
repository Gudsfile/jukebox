<script>
  import { apiPatch, apiPost } from '../api.js'

  let { mode, tagId: initialTagId = '', disc = null, onSaved, onCancel } = $props()

  let tagId = $state(initialTagId)
  let uri = $state(disc?.uri ?? '')
  let artist = $state(disc?.metadata.artist ?? '')
  let album = $state(disc?.metadata.album ?? '')
  let track = $state(disc?.metadata.track ?? '')
  let playlist = $state(disc?.metadata.playlist ?? '')
  let shuffle = $state(disc?.option.shuffle ?? false)
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
    <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
    <button type="button" onclick={onCancel}>Cancel</button>
  </div>
</form>
