<script>
  import { onMount } from 'svelte'
  import { apiDelete, apiGet } from '../api.js'
  import { toastStore } from '../stores/toastStore.js'
  import DiscForm from '../components/DiscForm.svelte'
  import { searchDiscs } from '../library/search.js'
  import { ALL, SHUFFLE_OFF, SHUFFLE_ON, filterDiscs, isFiltering, typeOptions } from '../library/filter.js'

  let { intent = null, onIntentConsumed } = $props()

  let discs = $state({})
  let loading = $state(true)
  let error = $state(null)
  let formMode = $state(null) // null | { type: 'create', tagId } | { type: 'edit', tagId, disc }
  let currentTagId = $state(null)
  let copiedTagId = $state(null)
  let deleteError = $state(null)
  let searchQuery = $state('')
  let typeFilter = $state(ALL)
  let shuffleFilter = $state(ALL)
  let typeSelect = $state(null)

  const allEntries = $derived(Object.entries(discs))
  const availableTypes = $derived(typeOptions(allEntries))
  const visibleEntries = $derived(
    filterDiscs(searchDiscs(allEntries, searchQuery), { type: typeFilter, shuffle: shuffleFilter }),
  )
  const filtering = $derived(isFiltering({ type: typeFilter, shuffle: shuffleFilter }))
  const noResultsMessage = $derived.by(() => {
    const query = searchQuery.trim()
    if (!query) return 'No disc matches the current filters'
    return filtering ? `No disc matches “${query}” with the current filters` : `No disc matches “${query}”`
  })

  function clearFilters() {
    typeFilter = ALL
    shuffleFilter = ALL
    // The Clear button disappears with the filters: keep keyboard focus in the toolbar.
    typeSelect?.focus()
  }

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
      // A delete or edit can remove the last disc of the filtered type: don't keep an
      // invisible filter that hides everything.
      if (typeFilter !== ALL && !availableTypes.includes(typeFilter)) typeFilter = ALL
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
    toastStore.showToast('💿 Disc saved.')
  }

  async function copyUri(tagId, uri) {
    await navigator.clipboard.writeText(uri)
    copiedTagId = tagId
    setTimeout(() => {
      if (copiedTagId === tagId) copiedTagId = null
    }, 1500)
  }

  function typeIcon(displayType) {
    return displayType.split(' ')[0]
  }

  function typeLabel(displayType) {
    const spaceIndex = displayType.indexOf(' ')
    return spaceIndex === -1 ? '' : displayType.slice(spaceIndex + 1)
  }

  async function handleDelete(tagId) {
    if (!confirm(`Delete disc "${tagId}"?`)) return
    try {
      await apiDelete(`/discs/${tagId}`)
      deleteError = null
      await loadDiscs()
      toastStore.showToast('💿 Disc deleted.')
    } catch (err) {
      deleteError = err.body?.detail ?? err.message
    }
  }
</script>

<div class="page-header">
  <h2>Library</h2>
  {#if !formMode}
    <button onclick={() => openCreate()}>Add disc</button>
  {/if}
</div>

{#if formMode?.type === 'create'}
  <DiscForm mode="create" tagId={formMode.tagId} onSaved={handleSaved} onCancel={closeForm} />
{:else if formMode?.type === 'edit'}
  <DiscForm mode="edit" tagId={formMode.tagId} disc={formMode.disc} onSaved={handleSaved} onCancel={closeForm} />
{:else}
  {#if loading}
    <p>Loading…</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if Object.keys(discs).length === 0}
    <p>No disc found</p>
  {:else}
    {#if deleteError}
      <p class="error">{deleteError}</p>
    {/if}
    <div class="library-toolbar">
      <input
        type="search"
        class="library-search"
        placeholder="Search tag, title, artist, URI…"
        aria-label="Search discs"
        bind:value={searchQuery}
      />
      <div class="library-filters" role="group" aria-label="Filter discs">
        <label>
          Type
          <select bind:this={typeSelect} bind:value={typeFilter}>
            <option value={ALL}>All types</option>
            {#each availableTypes as displayType (displayType)}
              <option value={displayType}>{displayType}</option>
            {/each}
          </select>
        </label>
        <label>
          Shuffle
          <select bind:value={shuffleFilter}>
            <option value={ALL}>Any</option>
            <option value={SHUFFLE_ON}>On</option>
            <option value={SHUFFLE_OFF}>Off</option>
          </select>
        </label>
        {#if filtering}
          <button type="button" class="btn-secondary" onclick={clearFilters}>Clear filters</button>
        {/if}
      </div>
    </div>
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
        {#each visibleEntries as [tagId, disc] (tagId)}
          <tr>
            <td class="spin-cell">
              {#if tagId === currentTagId}
                <span class="tag-spin" aria-hidden="true">💿</span>
              {/if}
            </td>
            <td class="tag">{tagId}</td>
            <td class="uri" title={disc.uri}>
              <span class="uri-row">
                <span class="uri-text">{disc.uri}</span>
                <button
                  type="button"
                  class="uri-copy"
                  onclick={() => copyUri(tagId, disc.uri)}
                  aria-label={copiedTagId === tagId ? 'Copied' : 'Copy URI'}
                >
                  {copiedTagId === tagId ? '✅' : '📋'}
                </button>
              </span>
            </td>
            <td class="type">
              <span class="type-icon">{typeIcon(disc.display_type)}</span>
              <span class="type-label">{typeLabel(disc.display_type)}</span>
            </td>
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
        {:else}
          <tr>
            <td colspan="7" class="no-results">{noResultsMessage}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
{/if}
