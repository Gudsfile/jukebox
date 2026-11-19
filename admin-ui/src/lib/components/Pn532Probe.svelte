<script>
  import { apiPost } from '../api.js'
  import ConfirmDialog from './ConfirmDialog.svelte'
  import { PIN_FIELDS, formatPin, profileLabel } from '../pn532/format.js'

  // Probes the reader with the saved config. The probe opens the SPI bus that a running `jukebox` with the
  // PN532 reader also uses, so it only runs once the user confirms the warning.
  let { profiles } = $props()

  const WARNING =
    'Probing while jukebox runs with the PN532 reader can disturb it: both use the same SPI bus. Stop jukebox first if you can.'

  let probeOpener = $state(null) // the Probe button while its confirmation is open
  let probing = $state(false)
  let result = $state(null)
  let error = $state(null)

  function askProbe(event) {
    probeOpener = event.currentTarget
  }

  async function confirmProbe() {
    probeOpener = null
    probing = true
    result = null
    error = null
    try {
      result = await apiPost('/pn532/probe')
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      probing = false
    }
  }

  function formatPins(pins) {
    return PIN_FIELDS.map((field) => `${field.label} ${formatPin(pins[field.key])}`).join(', ')
  }
</script>

<div class="panel">
  <h3>Probe</h3>
  <p class="probe-warning">{WARNING}</p>
  <div class="row-actions">
    <button onclick={askProbe} disabled={probing}>{probing ? 'Probing…' : 'Probe'}</button>
  </div>

  {#if result}
    <div class="probe-result" role="status">
      <p>Probed with: {profileLabel(profiles, result.board_profile)}, {result.protocol.toUpperCase()}</p>
      <p>Pins: {formatPins(result.pins)}</p>
      <p>Firmware version: {result.firmware_version}</p>
      <p>{result.uid ? `Tag UID: ${result.uid}` : 'No tag detected'}</p>
    </div>
  {:else if error}
    <p class="error" role="alert">{error}</p>
  {/if}
</div>

{#if probeOpener}
  <ConfirmDialog
    title="Probe the PN532 reader?"
    message={WARNING}
    confirmLabel="Probe"
    onConfirm={confirmProbe}
    onCancel={() => (probeOpener = null)}
    returnFocus={probeOpener}
  />
{/if}

<style>
  .probe-warning {
    font-size: 0.9em;
    color: var(--danger);
  }
</style>
