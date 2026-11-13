<script>
  import Modal from './Modal.svelte'

  // Asks for a second validation before a destructive action: only the confirm button runs it; Cancel,
  // Escape, the close button and the backdrop all call `onCancel`.
  let { title, message, confirmLabel, onConfirm, onCancel, returnFocus = null } = $props()

  const messageId = `confirm-message-${Math.random().toString(36).slice(2)}`
</script>

<Modal {title} onClose={onCancel} {returnFocus} describedBy={messageId}>
  <p id={messageId}>{message}</p>
  <div class="modal-footer">
    <button type="button" class="btn-secondary" onclick={onCancel}>Cancel</button>
    <button type="button" class="btn-danger" onclick={onConfirm}>{confirmLabel}</button>
  </div>
</Modal>
