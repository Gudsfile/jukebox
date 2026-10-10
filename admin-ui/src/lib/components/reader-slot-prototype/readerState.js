// PROTOTYPE, throwaway: the same state / status / title derivation as ReaderSlot.svelte, shared by
// the collapsed variants so they only disagree on layout.
import { typeIcon } from '../../library/discType.js'

export function readerView(currentTag, disc) {
  const state = !currentTag ? 'empty' : currentTag.known_in_library ? 'known' : 'unknown'
  return {
    state,
    status: { empty: 'No disc detected', unknown: 'Unknown disc', known: 'Disc detected' }[state],
    title: {
      empty: 'Place a disc on the reader',
      unknown: 'New disc…',
      known: disc?.display_title ?? currentTag?.tag_id,
    }[state],
    icon: { empty: '💿', unknown: '?', known: disc ? typeIcon(disc.display_type) : '💿' }[state],
  }
}
