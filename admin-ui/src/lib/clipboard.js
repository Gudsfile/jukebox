// `navigator.clipboard` only exists in secure contexts (HTTPS or localhost): over plain HTTP on a
// LAN hostname (e.g. http://jukebox.local) it is undefined. Fall back to the deprecated
// `execCommand('copy')`, which only needs a user gesture.
export async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text)
      return
    } catch {
      // writeText can exist and still reject (e.g. NotAllowedError): try the fallback before giving up.
    }
  }
  copyWithExecCommand(text)
}

function copyWithExecCommand(text) {
  const previousFocus = document.activeElement
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.setAttribute('readonly', '')
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  try {
    textarea.select()
    // iOS Safari may not select anything in a readonly textarea with select() alone.
    textarea.setSelectionRange(0, text.length)
    if (!document.execCommand('copy')) throw new Error('Copy command was rejected')
  } finally {
    textarea.remove()
    // select() moved the focus to the textarea: give it back (e.g. to the copy button) so keyboard
    // and screen reader users don't land back on <body>.
    previousFocus?.focus()
  }
}
