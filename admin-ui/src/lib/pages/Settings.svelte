<script>
  import { onMount } from 'svelte'
  import { apiGet } from '../api.js'
  import SettingForm from '../components/SettingForm.svelte'

  let settings = $state([])
  let effectiveSettingsError = $state(null)
  let loading = $state(true)
  let error = $state(null)
  let editingPath = $state(null)

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

  function formatValue(value) {
    if (value === null || value === undefined) return 'null'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  let sections = $derived(groupBySection(settings))
  let editingSetting = $derived(settings.find((setting) => setting.path === editingPath) ?? null)

  function openEdit(path) {
    editingPath = path
  }

  function closeForm() {
    editingPath = null
  }

  async function handleSaved() {
    editingPath = null
    await loadSettings()
  }
</script>

<h2>Settings</h2>

{#if editingSetting}
  <SettingForm setting={editingSetting} onSaved={handleSaved} onCancel={closeForm} />
{:else if loading}
  <p>Loading…</p>
{:else if error}
  <p class="error">{error}</p>
{:else}
  {#if effectiveSettingsError}
    <p class="error">{effectiveSettingsError} Persisted overrides are still shown below.</p>
  {/if}

  {#each sections as section (section.section)}
    <h3>{section.label}</h3>
    <table>
      <thead>
        <tr>
          <th>Setting</th>
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
              <div class="path">{setting.path}</div>
            </td>
            <td>{formatValue(setting.effective_value)}</td>
            <td>{setting.provenance}</td>
            <td><button onclick={() => openEdit(setting.path)}>Edit</button></td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/each}
{/if}
