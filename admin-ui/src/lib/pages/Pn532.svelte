<script>
  import { onMount } from 'svelte'
  import { apiGet } from '../api.js'
  import { toastStore } from '../stores/toastStore.js'
  import Pn532Form from '../components/Pn532Form.svelte'
  import PinoutDiagram from '../components/PinoutDiagram.svelte'
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
  <div class="pn532-layout">
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
      <div class="row-actions">
        <button onclick={openEdit}>Edit</button>
      </div>
    </div>

    <div class="panel">
      <h3>Wiring</h3>
      <PinoutDiagram profile={config.board_profile} resolved={config.resolved} />
    </div>
  </div>
{/if}

<style>
  /* Side by side on wide screens: the configuration on the left, its wiring on the right. */
  @media (min-width: 1024px) {
    .pn532-layout {
      display: grid;
      grid-template-columns: minmax(16rem, 1fr) minmax(0, 2fr);
      gap: 16px;
      align-items: start;
    }
  }
</style>
