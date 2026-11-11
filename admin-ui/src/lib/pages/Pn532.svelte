<script>
  import { onMount } from 'svelte'
  import { apiGet } from '../api.js'
  import { toastStore } from '../stores/toastStore.js'
  import Pn532Form from '../components/Pn532Form.svelte'
  import { PIN_FIELDS, formatPin, profileLabel } from '../pn532/format.js'

  let config = $state(null)
  let loading = $state(true)
  let error = $state(null)
  let editing = $state(false)

  async function load() {
    loading = true
    error = null
    try {
      config = await apiGet('/pn532')
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      loading = false
    }
  }

  onMount(load)

  function isOverridden(key) {
    return config.overrides[key] !== null
  }

  function openEdit() {
    editing = true
  }

  function closeEdit() {
    editing = false
  }

  function handleSaved(saved, action) {
    config = saved
    editing = false
    toastStore.showToast(action === 'reset' ? '🔌 PN532 pins reset to profile defaults.' : '🔌 PN532 settings saved.')
  }
</script>

<div class="page-header">
  <h2>PN532</h2>
</div>

{#if loading}
  <p>Loading…</p>
{:else if error}
  <p class="error">{error}</p>
{:else if editing}
  <Pn532Form {config} onSaved={handleSaved} onCancel={closeEdit} />
{:else}
  <div class="panel">
    <h3>Effective configuration</h3>
    <p>Profile: {profileLabel(config.profiles, config.board_profile)}</p>
    <p>Protocol: {config.protocol.toUpperCase()}</p>
    {#each PIN_FIELDS as field (field.key)}
      <p>
        {field.label}: {formatPin(config.resolved[field.key])}
        {#if isOverridden(field.key)}<span class="badge badge-configured">Override</span>{/if}
      </p>
    {/each}
  </div>

  <div class="row-actions">
    <button onclick={openEdit}>Edit</button>
  </div>
{/if}
