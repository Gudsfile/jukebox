<script>
  import { untrack } from 'svelte'
  import { apiPut } from '../api.js'
  import { PIN_FIELDS, formatPin } from '../pn532/format.js'

  let { config, onSaved, onCancel } = $props()

  function toInput(pin) {
    return pin ?? ''
  }

  function toPin(value) {
    return value === '' || value === null || value === undefined ? null : Number(value)
  }

  let boardProfile = $state(untrack(() => config.board_profile))
  let pins = $state(
    untrack(() => Object.fromEntries(PIN_FIELDS.map(({ key }) => [key, toInput(config.overrides[key])]))),
  )
  let error = $state(null)
  let saving = $state(false)

  let profileDefaults = $derived(config.profiles.find((profile) => profile.name === boardProfile)?.defaults ?? {})
  let hasOverrides = $derived(PIN_FIELDS.some(({ key }) => config.overrides[key] !== null))

  async function save(action, payload) {
    error = null
    saving = true
    try {
      onSaved(await apiPut('/pn532', payload), action)
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      saving = false
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    return save('save', {
      board_profile: boardProfile,
      spi: Object.fromEntries(PIN_FIELDS.map(({ key }) => [key, toPin(pins[key])])),
    })
  }

  function handleReset() {
    return save('reset', {
      board_profile: config.board_profile,
      spi: Object.fromEntries(PIN_FIELDS.map(({ key }) => [key, null])),
    })
  }
</script>

<form class="form-card" onsubmit={handleSubmit}>
  <h3>Edit PN532 Configuration</h3>
  <p>Pick the board profile, then override any pin it gets wrong. Leave a pin empty to use the profile default.</p>
  <p>Changes take effect after restart.</p>

  <label>
    Board profile
    <select bind:value={boardProfile}>
      {#each config.profiles as profile (profile.name)}
        <option value={profile.name}>{profile.label}</option>
      {/each}
    </select>
  </label>

  <table>
    <caption>Profile defaults (BCM)</caption>
    <thead>
      <tr>
        <th>Profile</th>
        {#each PIN_FIELDS as field (field.key)}
          <th>{field.label}</th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each config.profiles as profile (profile.name)}
        <tr class:active={profile.name === boardProfile}>
          <td>{profile.label}</td>
          {#each PIN_FIELDS as field (field.key)}
            <td>{formatPin(profile.defaults[field.key])}</td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>

  <fieldset>
    <legend>SPI pin overrides (BCM)</legend>
    {#each PIN_FIELDS as field (field.key)}
      <label>
        {field.label}
        <input
          type="number"
          min="0"
          step="1"
          placeholder={`Profile default: ${formatPin(profileDefaults[field.key])}`}
          bind:value={pins[field.key]}
        />
      </label>
    {/each}
  </fieldset>

  {#if hasOverrides}
    <p class="path">Reset removes every pin override; the saved profile then uses its default pins.</p>
  {/if}

  {#if error}
    <p class="error">{error}</p>
  {/if}

  <div class="actions">
    <button type="submit" class="btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
    {#if hasOverrides}
      <button type="button" class="btn-danger" onclick={handleReset} disabled={saving}>Reset</button>
    {/if}
    <button type="button" class="btn-secondary" onclick={onCancel}>Cancel</button>
  </div>
</form>
