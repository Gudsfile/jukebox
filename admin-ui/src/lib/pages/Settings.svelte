<script>
  import { onMount } from 'svelte'
  import { apiDownload, apiGet } from '../api.js'
  import { toastStore } from '../stores/toastStore.js'
  import RestoreDialog from '../components/RestoreDialog.svelte'
  import SettingBadges from '../components/SettingBadges.svelte'
  import SettingForm from '../components/SettingForm.svelte'
  import { formatProvenance, formatValue, scrollableValueAttributes } from '../settings/format.js'
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
  let restoring = $state(false)
  let restoreOpener = $state(null)
  let moreExports = $state(false)

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

  async function handleImported(kind, result) {
    restoring = false
    if (kind === 'all') {
      await loadSettings()
      toastStore.showToast(`💾 Backup imported: ${result.library.disc_count} discs. ${result.settings.message}`)
    } else if (kind === 'settings') {
      await loadSettings()
      toastStore.showToast(`⚙️ ${result.message}`)
    } else {
      toastStore.showToast(`📚 Library imported: ${result.disc_count} discs.`)
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
    <div class="settings-scroll">
      <table class="settings">
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
              <td>
                <div
                  class="setting-value"
                  {...scrollableValueAttributes(setting.default_value, `${setting.label}, default`)}
                >
                  {formatValue(setting.default_value)}
                </div>
              </td>
              <td>
                <div
                  class="setting-value"
                  {...scrollableValueAttributes(
                    setting.is_persisted ? setting.persisted_value : null,
                    `${setting.label}, persisted`,
                  )}
                >
                  {#if setting.is_persisted}
                    {formatValue(setting.persisted_value)}
                  {:else}
                    <span class="path">—</span>
                  {/if}
                </div>
              </td>
              <td>
                <div
                  class="setting-value"
                  {...scrollableValueAttributes(setting.effective_value, `${setting.label}, effective value`)}
                >
                  {formatValue(setting.effective_value)}
                </div>
              </td>
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
    </div>
  {:else}
    {#if searchQuery.trim()}
      <p class="no-results">No setting matches “{searchQuery.trim()}”</p>
    {/if}
  {/each}
{/if}

{#if !editingSetting}
  <h3 id="backup-title">Backup</h3>
  <section class="backup-card" aria-labelledby="backup-title">
    <p>Save the library and the persisted settings of this jukebox in one archive, or restore them from a backup.</p>
    <div class="backup-actions">
      <button class="btn-primary" onclick={() => exportFile('/export/all')}>Download backup (.zip)</button>
      <button
        class="btn-secondary"
        onclick={(event) => {
          restoreOpener = event.currentTarget
          restoring = true
        }}
      >
        Restore…
      </button>
    </div>
    <button
      class="link-button"
      aria-expanded={moreExports}
      aria-controls="backup-exports"
      onclick={() => (moreExports = !moreExports)}
    >
      More export options
    </button>
    {#if moreExports}
      <ul id="backup-exports" class="backup-exports">
        <li>
          <button class="link-button" onclick={() => exportFile('/export/library')}>Library (library.json)</button>
        </li>
        <li>
          <button class="link-button" onclick={() => exportFile('/export/settings')}>Settings (settings.json)</button>
        </li>
      </ul>
    {/if}
  </section>
{/if}

{#if restoring}
  <RestoreDialog onClose={() => (restoring = false)} onImported={handleImported} returnFocus={restoreOpener} />
{/if}
