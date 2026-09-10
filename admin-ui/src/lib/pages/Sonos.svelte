<script>
  import { onMount } from 'svelte'
  import { ApiError, apiGet, apiPost } from '../api.js'
  import SonosSelectionForm from '../components/SonosSelectionForm.svelte'

  const STATUS_LABELS = {
    available: 'Available',
    partial: 'Partially available',
    unavailable: 'Unavailable',
    not_selected: 'Not selected',
  }

  let selection = $state(null) // { selected_group, availability }
  let speakers = $state([])
  let loading = $state(true)
  let discoveryError = $state(null)
  let error = $state(null)
  let editing = $state(false)

  async function load() {
    loading = true
    discoveryError = null
    error = null
    try {
      selection = await apiGet('/sonos/selection')
      speakers = await apiGet('/sonos/speakers')
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        discoveryError = err.body?.detail ?? 'Sonos discovery unavailable.'
      } else {
        error = err.message
      }
    } finally {
      loading = false
    }
  }

  onMount(load)

  let speakersByUid = $derived(Object.fromEntries(speakers.map((speaker) => [speaker.uid, speaker])))

  function memberLabel(uid) {
    const speaker = speakersByUid[uid]
    return speaker ? `${speaker.name} [${uid}]` : uid
  }

  function speakerSelectionLabel(uid) {
    const group = selection?.selected_group
    if (!group) return 'Available'
    if (group.coordinator_uid === uid) return 'Coordinator'
    if (group.members.some((member) => member.uid === uid)) return 'Selected'
    return 'Available'
  }

  function openEdit() {
    editing = true
  }

  function closeEdit() {
    editing = false
  }

  async function handleSaved() {
    editing = false
    await load()
  }

  async function handleClearSelection() {
    await apiPost('/settings/reset', { path: 'jukebox.player.sonos.selected_group' })
    await load()
  }
</script>

<h2>Sonos</h2>

{#if editing}
  <SonosSelectionForm
    speakers={speakers}
    selectedGroup={selection?.selected_group ?? null}
    onSaved={handleSaved}
    onCancel={closeEdit}
  />
{:else if loading}
  <p>Loading…</p>
{:else if error}
  <p class="error">{error}</p>
{:else}
  {#if discoveryError}
    <p class="error">Sonos discovery unavailable: {discoveryError}</p>
  {/if}

  <div class="panel">
    <h3>Saved selection</h3>
    {#if !selection?.selected_group}
      <p>No Sonos speaker selection is currently saved.</p>
    {:else}
      <p>Status: {STATUS_LABELS[selection.availability.status] ?? selection.availability.status}</p>
      <p>Coordinator: {memberLabel(selection.selected_group.coordinator_uid)}</p>
      <p>Members: {selection.selected_group.members.map((member) => memberLabel(member.uid)).join(', ')}</p>
    {/if}
  </div>

  <div class="row-actions">
    <button onclick={openEdit}>Edit selection</button>
    {#if selection?.selected_group}
      <button class="btn-danger" onclick={handleClearSelection}>Clear saved selection</button>
    {/if}
  </div>

  {#if !discoveryError}
    <h3>Discovered speakers</h3>
    {#if speakers.length === 0}
      <p>No visible Sonos speakers found.</p>
    {:else}
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Host</th>
            <th>Household</th>
            <th>Selection</th>
          </tr>
        </thead>
        <tbody>
          {#each speakers as speaker (speaker.uid)}
            <tr>
              <td>{speaker.name}</td>
              <td>{speaker.host}</td>
              <td>{speaker.household_id}</td>
              <td class="center">{speakerSelectionLabel(speaker.uid)}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    {/if}
  {/if}
{/if}
