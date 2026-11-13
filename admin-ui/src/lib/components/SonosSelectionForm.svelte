<script>
  import { untrack } from 'svelte'
  import { apiPost, apiPut } from '../api.js'

  let { speakers, selectedGroup, onSaved, onCancel } = $props()

  function initialUids() {
    if (selectedGroup) return selectedGroup.members.map((member) => member.uid)
    return speakers[0] ? [speakers[0].uid] : []
  }

  let selectedUids = $state(untrack(() => new Set(initialUids())))
  let coordinatorUid = $state(untrack(() => selectedGroup?.coordinator_uid ?? initialUids()[0] ?? ''))
  let error = $state(null)
  let saving = $state(false)

  function toggleSpeaker(uid) {
    const next = new Set(selectedUids)
    if (next.has(uid)) {
      next.delete(uid)
    } else {
      next.add(uid)
    }
    selectedUids = next
  }

  async function handleSubmit(event) {
    event.preventDefault()
    error = null
    saving = true
    try {
      await apiPut('/sonos/selection', {
        uids: [...selectedUids],
        coordinator_uid: coordinatorUid,
      })
      onSaved('save')
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      saving = false
    }
  }

  async function handleClear() {
    error = null
    saving = true
    try {
      await apiPost('/settings/reset', { path: 'jukebox.player.sonos.selected_group' })
      onSaved('clear')
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      saving = false
    }
  }
</script>

<form class="form-card" onsubmit={handleSubmit}>
  <h3>Edit Sonos Selection</h3>
  <p>Choose one or more visible speakers and select the coordinator used for playback.</p>
  <p>Changes take effect after restart.</p>

  <fieldset>
    <legend>Speakers</legend>
    {#each speakers as speaker (speaker.uid)}
      <label class="checkbox">
        <input type="checkbox" checked={selectedUids.has(speaker.uid)} onchange={() => toggleSpeaker(speaker.uid)} />
        {speaker.name} ({speaker.host})
      </label>
    {/each}
  </fieldset>

  <label>
    Coordinator
    <select bind:value={coordinatorUid}>
      {#each speakers as speaker (speaker.uid)}
        <option value={speaker.uid}>{speaker.name} ({speaker.host})</option>
      {/each}
    </select>
  </label>

  {#if selectedGroup}
    <p class="path">Clear saved selection removes the saved speakers and coordinator.</p>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div class="actions">
    <button type="submit" class="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
    {#if selectedGroup}
      <button type="button" class="btn-danger" onclick={handleClear} disabled={saving}>Clear saved selection</button>
    {/if}
    <button type="button" class="btn-secondary" onclick={onCancel}>Cancel</button>
  </div>
</form>
