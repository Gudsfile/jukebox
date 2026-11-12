<script>
  import { onMount } from 'svelte'

  // A modal dialog, mounted while open: focus moves in and stays trapped, Escape, the close button and
  // the backdrop close it unless `closable` is false, and focus goes back to the element that opened it.
  // Keys are listened to on the window: a step change can remove the focused element and drop the
  // focus on <body>, and Escape and Tab must still work then.
  let { title, onClose, closable = true, returnFocus = null, children } = $props()

  const FOCUSABLE = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  const titleId = `modal-title-${Math.random().toString(36).slice(2)}`

  let dialog
  let pressedOnBackdrop = false

  function focusables() {
    return [...dialog.querySelectorAll(FOCUSABLE)].filter(
      (element) => !element.disabled && !element.closest('[hidden]'),
    )
  }

  onMount(() => {
    // Safari and Firefox on macOS do not focus a button on click: prefer the opener given explicitly.
    const active = document.activeElement
    const opener = returnFocus ?? (active && active !== document.body ? active : null)
    ;(focusables()[0] ?? dialog).focus()
    return () => opener?.focus?.()
  })

  function close() {
    if (closable) onClose()
  }

  function onWindowKeydown(event) {
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
      return
    }
    if (event.key !== 'Tab') return
    const elements = focusables()
    if (!elements.length) {
      event.preventDefault()
      dialog.focus()
      return
    }
    const first = elements[0]
    const last = elements.at(-1)
    if (!dialog.contains(document.activeElement)) {
      event.preventDefault()
      ;(event.shiftKey ? last : first).focus()
    } else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault()
      first.focus()
    }
  }

  // Close only when the press and the release both happen on the backdrop: a text selection started in
  // the dialog and released outside must not close it.
  function onBackdropMousedown(event) {
    pressedOnBackdrop = event.target === event.currentTarget
  }

  function onBackdropClick(event) {
    if (pressedOnBackdrop && event.target === event.currentTarget) close()
    pressedOnBackdrop = false
  }

  // A file dropped anywhere while the dialog is open must not be opened by the browser, which would leave
  // the admin UI.
  function preventFileDrop(event) {
    event.preventDefault()
  }
</script>

<svelte:window onkeydown={onWindowKeydown} />

<div
  class="modal-backdrop"
  role="presentation"
  onmousedown={onBackdropMousedown}
  onclick={onBackdropClick}
  ondragover={preventFileDrop}
  ondrop={preventFileDrop}
>
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} tabindex="-1" bind:this={dialog}>
    <header class="modal-header">
      <h3 id={titleId}>{title}</h3>
      <button class="modal-close" aria-label="Close" disabled={!closable} onclick={close}>✕</button>
    </header>
    {@render children()}
  </div>
</div>
