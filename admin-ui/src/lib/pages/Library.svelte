<script>
  import { onMount } from 'svelte'
  import { apiDelete, apiGet } from '../api.js'
  import DiscForm from '../components/DiscForm.svelte'

  let discs = $state({})
  let loading = $state(true)
  let error = $state(null)
  let formMode = $state(null) // null | 'create' | { tagId, disc }

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

  function openCreate() {
    formMode = 'create'
  }

  function openEdit(tagId) {
    formMode = { tagId, disc: discs[tagId] }
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

{#if formMode === 'create'}
  <DiscForm mode="create" onSaved={handleSaved} onCancel={closeForm} />
{:else if formMode}
  <DiscForm mode="edit" tagId={formMode.tagId} disc={formMode.disc} onSaved={handleSaved} onCancel={closeForm} />
{:else}
  <button onclick={openCreate}>Add disc</button>

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
