<script>
  import { onDestroy, tick } from 'svelte'
  import { apiUpload } from '../api.js'
  import { BACKUP_FILE_ACCEPT, BACKUP_KINDS, detectBackupKind } from '../backup/backup.js'
  import ImportSummary from './ImportSummary.svelte'
  import Modal from './Modal.svelte'

  // Restores one file in two steps: choose or drop it, then review what it changes and confirm.
  // Nothing is written before "Replace".
  let { onClose, onImported, returnFocus = null } = $props()

  let fileInput = $state(null)
  let dropzone = $state(null)
  let reviewHeading = $state(null)
  let errorMessage = $state(null)
  let pending = $state(null)
  let error = $state(null)
  let reading = $state(false)
  let replacing = $state(false)
  let dragging = $state(false)
  let previewController = null

  let busy = $derived(reading || replacing)

  // Reading a file and previewing it write nothing: closing the dialog then just cancels the preview.
  onDestroy(() => previewController?.abort())

  async function load(file) {
    if (!file) return
    error = null
    reading = true
    previewController = new AbortController()
    try {
      const kind = await detectBackupKind(file)
      const summary = await apiUpload(`${BACKUP_KINDS[kind].path}/preview`, file, {
        signal: previewController.signal,
      })
      pending = { kind, file, summary }
    } catch (err) {
      if (err.name === 'AbortError') return
      error = err.body?.detail ?? err.message
    } finally {
      reading = false
      previewController = null
    }
    await focusStep()
  }

  // A step change removes the focused element (or disables it while busy): put the focus back in the
  // dialog, on the error if any, else at the start of the current step.
  async function focusStep() {
    await tick()
    ;(errorMessage ?? (pending ? reviewHeading : dropzone))?.focus()
  }

  function onFileChange(event) {
    const file = event.currentTarget.files?.[0]
    // Reset the input so that picking the same file again triggers a new preview.
    event.currentTarget.value = ''
    load(file)
  }

  function onDrop(event) {
    event.preventDefault()
    dragging = false
    load(event.dataTransfer?.files?.[0])
  }

  function chooseAnother() {
    pending = null
    error = null
    focusStep()
  }

  async function replace() {
    const { kind, file } = pending
    error = null
    replacing = true
    try {
      const result = await apiUpload(BACKUP_KINDS[kind].path, file)
      await onImported(kind, result)
    } catch (err) {
      error = err.body?.detail ?? err.message
    } finally {
      replacing = false
    }
    if (error) await focusStep()
  }
</script>

<!-- No closing while replacing: an import still running would report its result to a closed dialog. -->
<Modal title="Restore a backup" {onClose} closable={!replacing} {returnFocus}>
  <ol class="restore-steps">
    <li class:current={!pending} class:done={pending} aria-current={pending ? undefined : 'step'}>Choose a file</li>
    <li class:current={pending} aria-current={pending ? 'step' : undefined}>Review and confirm</li>
  </ol>

  {#if error}
    <p class="error" role="alert" tabindex="-1" bind:this={errorMessage}>{error}</p>
  {/if}

  {#if !pending}
    <input
      type="file"
      accept={BACKUP_FILE_ACCEPT}
      hidden
      aria-label="Backup file"
      bind:this={fileInput}
      onchange={onFileChange}
    />
    <button
      class="dropzone"
      class:dragging
      bind:this={dropzone}
      disabled={busy}
      onclick={() => fileInput.click()}
      ondragover={(event) => {
        event.preventDefault()
        dragging = true
      }}
      ondragleave={() => (dragging = false)}
      ondrop={onDrop}
    >
      <strong>{busy ? 'Reading the file…' : 'Drop a file here, or click to choose'}</strong>
      <span class="path">A full backup .zip, or a library or settings .json file</span>
    </button>
  {:else}
    {@const kind = BACKUP_KINDS[pending.kind]}
    <h4 class="restore-review" tabindex="-1" bind:this={reviewHeading}>Review the changes</h4>
    <p class="restore-file">
      <span class="badge">{kind.label}</span>
      {pending.file.name}
      <button class="link-button" disabled={busy} onclick={chooseAnother}>Choose another file</button>
    </p>
    <div class="restore-diff">
      <ImportSummary kind={pending.kind} summary={pending.summary} />
    </div>
    <p class="restore-warning">This replaces the current {kind.replaces}. It cannot be undone.</p>
    <div class="modal-footer">
      <button class="btn-secondary" disabled={busy} onclick={onClose}>Cancel</button>
      <button class="btn-danger" disabled={busy} onclick={replace}>Replace {kind.replaces}</button>
    </div>
  {/if}
</Modal>
