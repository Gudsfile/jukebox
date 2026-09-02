<script>
  import { onMount } from 'svelte'
  import { apiDelete, apiGet } from '../api.js'
  import DiscForm from '../components/DiscForm.svelte'

  let { intent = null, onIntentConsumed } = $props()

  let discs = $state({})
  let loading = $state(true)
  let error = $state(null)
  let formMode = $state(null) // null | { type: 'create', tagId } | { type: 'edit', tagId, disc }
  let currentTagId = $state(null)

  $effect(() => {
    // Purely cosmetic: spins next to the matching row if it's on screen. No scroll,
    // no highlight — independent from the current-tag banner above.
    const source = new EventSource('/api/v1/current-tag/events')
    source.onmessage = (event) => {
      const data = JSON.parse(event.data)
      currentTagId = data?.known_in_library ? data.tag_id : null
    }
    return () => source.close()
  })

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
    <table class="discs">
      <colgroup>
        <col style="width: 24px" />
        <col style="width: 14%" />
        <col />
        <col style="width: 90px" />
        <col style="width: 28%" />
        <col style="width: 70px" />
        <col style="width: 130px" />
      </colgroup>
      <thead>
        <tr>
          <th></th>
          <th>Tag</th>
          <th>URI</th>
          <th>Type</th>
          <th>Title</th>
          <th>Shuffle</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each Object.entries(discs) as [tagId, disc] (tagId)}
          <tr>
            <td class="spin-cell">
              {#if tagId === currentTagId}
                <span class="tag-spin" aria-hidden="true">💿</span>
              {/if}
            </td>
            <td class="tag">{tagId}</td>
            <td class="uri" title={disc.uri}><span class="uri-text">{disc.uri}</span></td>
            <td class="type">{disc.display_type}</td>
            <td class="title">{disc.display_title}</td>
            <td class="center">
              <span
                class="shuffle-icon"
                class:active={disc.option.shuffle}
                role="img"
                aria-label={disc.option.shuffle ? 'Shuffle on' : 'Shuffle off'}
              >
                🔀
              </span>
            </td>
            <td class="row-actions">
              <button onclick={() => openEdit(tagId)}>Edit</button>
              <button class="btn-danger" onclick={() => handleDelete(tagId)}>Delete</button>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
{/if}
