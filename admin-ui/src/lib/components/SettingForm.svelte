<script>
  import { untrack } from 'svelte'
  import { apiPatch, apiPost } from '../api.js'

  let { setting, onSaved, onCancel } = $props()

  function formatInitialValue(current) {
    const value = current.is_persisted ? current.persisted_value : current.effective_value
    if (value === null || value === undefined) return ''
    if (current.field_type === 'object') return JSON.stringify(value, null, 2)
    return String(value)
  }

  let rawValue = $state(untrack(() => formatInitialValue(setting)))
  let error = $state(null)
  let saving = $state(false)

  function buildDottedPatch(path, value) {
    const parts = path.split('.')
    const patch = {}
    let cursor = patch
    for (const part of parts.slice(0, -1)) {
      cursor[part] = {}
      cursor = cursor[part]
    }
    cursor[parts.at(-1)] = value
    return patch
  }

  function coerceValue() {
    if (setting.choices.length > 0) return rawValue

    if (setting.field_type === 'integer') {
      const parsed = Number.parseInt(rawValue, 10)
      if (Number.isNaN(parsed)) throw new Error('Enter a valid integer.')
      return parsed
    }

    if (setting.field_type === 'number') {
      const parsed = Number.parseFloat(rawValue)
      if (Number.isNaN(parsed)) throw new Error('Enter a valid number.')
      return parsed
    }

    if (setting.field_type === 'object') {
      if (rawValue.trim() === '') return null
      try {
        return JSON.parse(rawValue)
      } catch {
        throw new Error('Enter valid JSON.')
      }
    }

    return rawValue
  }

  async function handleSubmit(event) {
    event.preventDefault()
    error = null
    saving = true
    try {
      const value = coerceValue()
      await apiPatch('/settings', buildDottedPatch(setting.path, value))
      onSaved()
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      saving = false
    }
  }

  async function handleReset() {
    error = null
    saving = true
    try {
      await apiPost('/settings/reset', { path: setting.path })
      onSaved()
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      saving = false
    }
  }
</script>

<form onsubmit={handleSubmit}>
  <h3>Edit {setting.label}</h3>
  <p class="path">{setting.path}</p>
  <p>{setting.description}</p>

  {#if setting.choices.length > 0}
    <select bind:value={rawValue}>
      {#each setting.choices as choice (choice.value)}
        <option value={choice.value}>{choice.label}</option>
      {/each}
    </select>
  {:else if setting.field_type === 'object'}
    <textarea bind:value={rawValue} rows="10" placeholder="Enter a JSON object. Leave blank to persist null."
    ></textarea>
  {:else}
    <input
      bind:value={rawValue}
      type={setting.field_type === 'integer' || setting.field_type === 'number' ? 'number' : 'text'}
    />
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div class="actions">
    <button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
    {#if setting.is_persisted}
      <button type="button" onclick={handleReset} disabled={saving}>Reset</button>
    {/if}
    <button type="button" onclick={onCancel}>Cancel</button>
  </div>
</form>
