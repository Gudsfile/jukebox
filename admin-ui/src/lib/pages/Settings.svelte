<script>
  import { onMount } from 'svelte'
  import { apiDownload, apiGet } from '../api.js'
  import { toastStore } from '../stores/toastStore.js'
  import SettingBadges from '../components/SettingBadges.svelte'
  import SettingForm from '../components/SettingForm.svelte'
  import { formatProvenance, formatValue } from '../settings/format.js'
  import { searchSettings } from '../settings/search.js'

  const SONOS_SELECTED_GROUP_PATH = 'jukebox.player.sonos.selected_group'
  const PN532_BOARD_PROFILE_PATH = 'jukebox.reader.pn532.board_profile'
  // Some browsers (Safari) read the blob after click() returns: keep its URL alive for a while (as FileSaver.js does).
  const REVOKE_DOWNLOAD_URL_DELAY_MS = 40_000

  let { onManageSpeakers, onConfigurePn532 } = $props()

  let settings = $state([])
  let effectiveSettingsError = $state(null)
  let loading = $state(true)
  let error = $state(null)
  let editingPath = $state(null)
  let searchQuery = $state('')

  async function loadSettings() {
    loading = true
    try {
      const response = await apiGet('/settings/displays')
      settings = response.settings
      effectiveSettingsError = response.effective_settings_error
      error = null
    } catch (err) {
      error = err.message
    } finally {
      loading = false
    }
  }

  onMount(loadSettings)

  function groupBySection(list) {
    const sections = []
    for (const setting of list) {
      const last = sections.at(-1)
      if (last && last.section === setting.section) {
        last.entries.push(setting)
      } else {
        sections.push({ section: setting.section, label: setting.section_label, entries: [setting] })
      }
    }
    return sections
  }

  let sections = $derived(groupBySection(searchSettings(settings, searchQuery)))
  let editingSetting = $derived(settings.find((setting) => setting.path === editingPath) ?? null)

  function openEdit(path) {
    editingPath = path
  }

  function closeForm() {
    editingPath = null
  }

  async function handleSaved(action) {
    editingPath = null
    await loadSettings()
    if (action === 'save') {
      toastStore.showToast('⚙️ Settings saved.')
    } else if (action === 'reset') {
      toastStore.showToast('⚙️ Settings reset to default.')
    }
  }

  async function exportFile(path) {
    try {
      const { blob, filename } = await apiDownload(path)
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = filename
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), REVOKE_DOWNLOAD_URL_DELAY_MS)
    } catch (err) {
      toastStore.showToast(`⚠️ Export failed: ${err.body?.detail ?? err.message}`)
    }
  }
</script>

<div class="page-header">
  <h2>Settings</h2>
</div>

{#snippet effectiveSettingsErrorBanner()}
  {#if effectiveSettingsError}
    <p class="error">{effectiveSettingsError} Persisted overrides are still shown below.</p>
  {/if}
{/snippet}

{#if editingSetting}
  {@render effectiveSettingsErrorBanner()}
  <SettingForm setting={editingSetting} onSaved={handleSaved} onCancel={closeForm} />
{:else if loading}
  <p>Loading…</p>
{:else if error}
  <p class="error">{error}</p>
{:else}
  {@render effectiveSettingsErrorBanner()}
  <div class="page-toolbar">
    <input
      type="search"
      class="search-input"
      placeholder="Search name, path, value, source…"
      aria-label="Search settings"
      bind:value={searchQuery}
    />
  </div>

  {#each sections as section (section.section)}
    <h3>{section.label}</h3>
    <table>
      <thead>
        <tr>
          <th>Setting</th>
          <th>Default</th>
          <th>Persisted</th>
          <th>Effective value</th>
          <th>Source</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        {#each section.entries as setting (setting.path)}
          <tr>
            <td>
              <strong>{setting.label}</strong>
              <SettingBadges {setting} />
              <div class="path">{setting.path}</div>
            </td>
            <td>{formatValue(setting.default_value)}</td>
            <td>
              {#if setting.is_persisted}
                {formatValue(setting.persisted_value)}
              {:else}
                <span class="path">—</span>
              {/if}
            </td>
            <td>{formatValue(setting.effective_value)}</td>
            <td>{formatProvenance(setting.provenance)}</td>
            <td>
              {#if setting.path === SONOS_SELECTED_GROUP_PATH}
                <button onclick={() => onManageSpeakers?.()}>Manage Speakers 🔊</button>
              {:else if setting.path === PN532_BOARD_PROFILE_PATH}
                <button onclick={() => onConfigurePn532?.()}>Configure PN532 🔌</button>
              {:else}
                <button onclick={() => openEdit(setting.path)}>Edit</button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {:else}
    {#if searchQuery.trim()}
      <p class="no-results">No setting matches “{searchQuery.trim()}”</p>
    {/if}
  {/each}
{/if}

{#if !editingSetting}
  <section class="backup">
    <h3>Backup</h3>
    <p>Download the library and the persisted settings as JSON files.</p>
    <div class="row-actions">
      <button class="btn-secondary" onclick={() => exportFile('/export/library')}>Export library</button>
      <button class="btn-secondary" onclick={() => exportFile('/export/settings')}>Export settings</button>
    </div>
  </section>
{/if}
