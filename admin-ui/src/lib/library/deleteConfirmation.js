// The confirmation of a disc deletion, the same from the table row and from the edit form.
export const DELETE_DISC_TITLE = 'Delete this disc?'

export function deleteDiscMessage(tagId, disc) {
  return `This removes “${disc?.display_title ?? tagId}” (${tagId}) from the library. It cannot be undone.`
}
