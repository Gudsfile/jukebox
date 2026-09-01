<script>
  import { onMount } from 'svelte'
  import { apiDelete, apiGet } from '../api.js'
  import DiscForm from '../components/DiscForm.svelte'

  let { intent = null, onIntentConsumed } = $props()

  let discs = $state({})
  let loading = $state(true)
  let error = $state(null)
  let formMode = $state(null) // null | { type: 'create', tagId } | { type: 'edit', tagId, disc }

  async function loadDiscs() {
    loading = true
    try {
      discs = await apiGet('/discs')
      error = null
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }

  onMount(loadDiscs)

  // Lets the current-tag banner (in App.svelte) jump here with "edit this disc" / "add this
  // disc" intent — consumed once discs are loaded, then cleared so it doesn't re-fire.
  $effect(() => {
    if (!intent || loading) return
    if (intent.type === 'edit') {
      openEdit(intent.tagId)
    } else {
      openCreate(intent.tagId)
    }
    onIntentConsumed?.()
  })

  function openCreate(prefillTagId = '') {
    formMode = { type: 'create', tagId: prefillTagId }
  }

  function openEdit(tagId) {
    formMode = { type: 'edit', tagId, disc: discs[tagId] }
  }

  function closeForm() {
    formMode = null
  }

  async function handleSaved() {
    formMode = null
    await loadDiscs()
  }

  async function handleDelete(tagId) {
    if (!confirm(`Delete disc "${tagId}"?`)) return
    await apiDelete(`/discs/${tagId}`)
    await loadDiscs()
  }
</script>

<h2>Library</h2>

{#if formMode?.type === 'create'}
  <DiscForm mode="create" tagId={formMode.tagId} onSaved={handleSaved} onCancel={closeForm} />
{:else if formMode?.type === 'edit'}
  <DiscForm mode="edit" tagId={formMode.tagId} disc={formMode.disc} onSaved={handleSaved} onCancel={closeForm} />
{:else}
  <button onclick={() => openCreate()}>Add disc</button>

  {#if loading}
    <p>Loading…</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if Object.keys(discs).length === 0}
    <p>No disc found</p>
  {:else}
    <table>
      <thead>
        <tr>
          <th>Tag</th>
          <th>URI</th>
          <th>Artist</th>
          <th>Album</th>
          <th>Track</th>
          <th>Playlist</th>
          <th>Shuffle</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each Object.entries(discs) as [tagId, disc] (tagId)}
          <tr>
            <td>{tagId}</td>
            <td>{disc.uri}</td>
            <td>{disc.metadata.artist ?? ''}</td>
            <td>{disc.metadata.album ?? ''}</td>
            <td>{disc.metadata.track ?? ''}</td>
            <td>{disc.metadata.playlist ?? ''}</td>
            <td>{disc.option.shuffle ? 'yes' : 'no'}</td>
            <td>
              <button onclick={() => openEdit(tagId)}>Edit</button>
              <button onclick={() => handleDelete(tagId)}>Delete</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
{/if}
