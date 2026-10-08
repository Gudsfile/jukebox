<script>
  import { onMount } from 'svelte'
  import { apiDelete, apiGet } from '../api.js'
  import { toastStore } from '../stores/toastStore.js'
  import DiscForm from '../components/DiscForm.svelte'
  import ReaderSlot from '../components/ReaderSlot.svelte'
  import { searchDiscs } from '../library/search.js'
  import { typeIcon, typeLabel } from '../library/discType.js'
  import { ALL, SHUFFLE_OFF, SHUFFLE_ON, filterDiscs, isFiltering, typeOptions } from '../library/filter.js'
  import { nextSort, sortEntries } from '../library/sort.js'

  let { intent = null, onIntentConsumed } = $props()

  let discs = $state({})
  let loading = $state(true)
  let error = $state(null)
  let formMode = $state(null) // null | { type: 'create', tagId } | { type: 'edit', tagId, disc }
  let currentTag = $state(null) // null | { tag_id, known_in_library }, pushed by the SSE stream
  let copiedTagId = $state(null)
  let deleteError = $state(null)
  let searchQuery = $state('')
  let typeFilter = $state(ALL)
  let shuffleFilter = $state(ALL)
  let typeSelect = $state(null)
  let sort = $state(null) // null (default order) | { key, direction: 'asc' | 'desc' }

  const currentTagId = $derived(currentTag?.known_in_library ? currentTag.tag_id : null)
  const allEntries = $derived(Object.entries(discs))
  const availableTypes = $derived(typeOptions(allEntries))
  const visibleEntries = $derived(
    sortEntries(filterDiscs(searchDiscs(allEntries, searchQuery), { type: typeFilter, shuffle: shuffleFilter }), sort),
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

  function ariaSort(key) {
    if (sort?.key !== key) return undefined
    return sort.direction === 'asc' ? 'ascending' : 'descending'
  }

  $effect(() => {
    // Feeds both the ReaderSlot console and the spinning disc next to the matching row.
    const source = new EventSource('/api/v1/current-tag/events')
    source.onmessage = (event) => {
      currentTag = JSON.parse(event.data)
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

{#snippet sortableHeader(key, label, align = undefined)}
  <th class={align} aria-sort={ariaSort(key)}>
    <button type="button" class="sort-button" onclick={() => (sort = nextSort(sort, key))}>
      {label}
      <span class="sort-indicator" aria-hidden="true">
        {sort?.key === key ? (sort.direction === 'asc' ? '▲' : '▼') : '↕'}
      </span>
    </button>
  </th>
{/snippet}

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
    <div class="discs-scroll">
      <table class="discs">
        <colgroup>
          <col style="width: 24px" />
          <col style="width: 14%" />
          <col />
          <col style="width: 90px" />
          <col style="width: 28%" />
          <col style="width: 90px" />
          <col style="width: 170px" />
        </colgroup>
        <thead>
          <tr>
            <th></th>
            {@render sortableHeader('tag', 'Tag')}
            <th>URI</th>
            {@render sortableHeader('type', 'Type')}
            {@render sortableHeader('title', 'Title', 'center')}
            {@render sortableHeader('shuffle', 'Shuffle', 'center')}
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
              <td>
                <div class="row-actions">
                  <button onclick={() => openEdit(tagId)}>Edit</button>
                  <button class="btn-danger" onclick={() => handleDelete(tagId)}>Delete</button>
                </div>
              </td>
            </tr>
          {:else}
            <tr>
              <td colspan="7" class="no-results">{noResultsMessage}</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}

<ReaderSlot
  {currentTag}
  disc={currentTagId ? discs[currentTagId] : undefined}
  actionsEnabled={!formMode}
  onAdd={openCreate}
  onEdit={openEdit}
/>
