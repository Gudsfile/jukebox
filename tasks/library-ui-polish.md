# Library UI Polish — Issues Backlog

Source: UX/product audit of the Svelte Library page (2026-09-02).

**Scope note:** all issues below target `admin-ui/` (the Svelte SPA) only. The old FastUI adapter (`ui_controller.py`, `ui_pages/`) is being removed per `docs/adr/0003-ui-framework-migration.md` and `tasks/plan.md` (Task 9, `tasks/todo.md`) — none of this backlog touches it.

These are retained design decisions from the audit conversation, not yet sequenced or estimated. Sequencing/estimation to happen at planning time, per item, when picked up.

---

## Issue 1: Current-tag player widget (3 states)

**Context:** The current `CurrentTagBanner` is a generic notification banner (color clashes with the rest of the palette, competes with page identity, unrelated states — reader/Sonos status, tag status — share one visual slot).

**Decision:** Replace the "current tag" behavior specifically with a dedicated "player" widget with three explicit states: nothing on the reader / known disc on the reader / unknown disc on the reader (propose add). Styled to evoke a physical jukebox display (rounded marquee-like shape, glowing edge colored per state), not a generic dashboard alert. This is the natural home for cover art later (see Issue 9).

Superseded ideas, explicitly dropped:
- A "ghost row" duplicating the current disc's data at the top of the table — redundant once the widget handles the unknown-tag "propose add" flow.
- Reordering the table to float the current-tag row to the top — reorder-under-cursor risk (misclick while another row is being edited/deleted) with no upside once the widget exists.

**Open question:** the generic `CurrentTagBanner` mechanism may still be needed for *other* statuses unrelated to tag detection (e.g. reader/Sonos connection issues) — not yet verified against the actual code. If confirmed, keep the banner for those cases; it is only replaced for the "current tag" feature specifically.

---

## Issue 2: Spinning disc emoji in the table row (bonus)

**Context:** Originally proposed as the primary "current tag" indicator; superseded by Issue 1's widget as the primary signal.

**Decision:** Keep it, but strictly as a secondary "wink" — a 💿 that spins next to the matching row **only when that row happens to be visible on screen**. No auto-scroll, no highlight/emphasis, no dependency on Issue 1. Purely decorative correlation, independent feature.

---

## Issue 3: Shuffle icon

**Context:** Current ✓/× glyphs for the Shuffle column visually clash with the adjacent red ✕-shaped Delete action — same shape, opposite meaning, in the same row.

**Decision:** Replace ✓/× with the shuffle glyph itself (🔀-style crossed arrows), filled/colored when active, outlined/dimmed when inactive. Matches the icon language already used in the Type column. Needs an `aria-label` ("Shuffle on/off") since it's icon-only.

---

## Issue 4: Tag column — de-emphasize, don't hide

**Context:** The admin UI's job is to make library/settings management easier than editing `library.json` or using the CLI — it is not the end-user interaction (that's the physical tap-to-play gesture). The raw NFC UID must stay visible with **zero extra click/hover**, since matching it against a physical tag or the current-tag widget is a real workflow. A free-text "label" field was considered and **rejected** — extra field, verbose, unnecessary for this use case.

**Decision:** Keep the raw UID, always visible, but lower its visual weight: monospace font, smaller size, muted color (reuse the existing `.path` treatment pattern already in `app.css` — `color: var(--text); font-size: 0.85em; opacity: 0.75`). No new data field.

---

## Issue 5: URI column — de-emphasize + truncate

**Context:** Same reasoning as Issue 4 — raw URI is legitimate, technical-user-facing content, must not require an extra click to *identify* which disc a row is. Ellipsis truncation (`.uri` class) was already intended in the current CSS but doesn't currently work correctly.

**Decision:** Same muted/monospace/smaller treatment as Issue 4. Truncation via ellipsis is fine — full value is available via the Edit form, no tooltip needed. Fix the existing truncation bug (`.uri` — `overflow: hidden; text-overflow: ellipsis` — not currently taking effect) as part of this issue.

---

## Issue 6: Click-to-copy on the URI cell

**Context:** Duplicate URIs already exist across different tags in the real library data (spotted during the audit) — reusing a URI across tags is a real behavior worth supporting.

**Decision:** Add a copy action, implemented as:
- A dedicated small copy icon/button next to the (truncated) text — **not** the whole cell as a click target, so native text selection still works.
- Copies the full underlying URI value, not the visually truncated string.
- Visible feedback on copy (clipboard writes are silent by default — needs a "copied" confirmation).
- A real `<button>` with `aria-label="Copy URI"` for keyboard/screen-reader accessibility.

Optional extension: same pattern on the Tag column (copy UID) — low cost once the mechanism exists, add only if a real need shows up.

---

## Issue 7: Color palette rework (light + dark)

**Context:** Current palette (`admin-ui/src/app.css`) is generic purple-accent-on-near-black/white, unrelated to the jukebox theme. Confirmed in code: theming is plain CSS custom properties + `@media (prefers-color-scheme: dark)`, no toggle, no framework — both light and dark must be designed explicitly, values are not simple inversions of each other (saturated hues need different lightness/saturation per mode to keep contrast).

**Decision:** New token set, same variable roles as today plus two new semantic ones for Issue 1's widget states:

| Variable | Light | Dark | Usage |
|---|---|---|---|
| `--bg` | `#FBF6EC` | `#17140F` | page background |
| `--text` | `#6B6153` | `#A79E8E` | secondary text |
| `--text-h` | `#1E1912` | `#F2ECE1` | headings, strong text |
| `--border` | `#E4DCC9` | `#3A3327` | dividers |
| `--accent` | `#A6690E` | `#E8A33D` | primary actions, active nav, focus |
| `--accent-bg` | `rgba(166,105,14,.10)` | `rgba(232,163,61,.15)` | active nav background |
| `--state-known` | `#1F8F80` | `#2FB8A6` | widget/row state: known disc |
| `--state-unknown` | `#93307D` | `#B3489A` | widget state: unknown disc / propose add |
| `--danger` | `#A83324` | `#C4432E` | Delete action (currently hardcoded `#c0392b` in `.btn-danger` — move to a variable as part of this issue) |

Verify contrast (esp. `--accent` and `--danger` as text/border color) in both modes when implementing, not just carry over the current hardcoded values.

---

## Issue 8a: Search

Free-text search across the library table (tag, title, artist, URI) to keep the table usable as it grows.

## Issue 8b: Sort

Sortable columns on the library table.

## Issue 8c: Filter

Filter the library table (e.g. by Type, by Shuffle on/off).

---

## Issue 9a: Cover art — POC with an external image source

Feasibility spike: fetch and display cover art from an external provider (e.g. Spotify's Web API) keyed off the disc's URI, read-only, no persistence. Confirms viability before committing to Issue 9b.

## Issue 9b: Cover art — manual image assignment

Allow assigning/uploading a cover image per disc, stored and served by the app, independent of Issue 9a's external-fetch feasibility.

---

## Issue 10: "Add disc" — placement/mechanism, not just styling

**Context:** flagged during manual review of the quick-win fixes (2026-09-02). Originally framed as "give it primary button styling" — **rejected**: the problem isn't the button's color, it's that it's badly placed, and a floating standalone button above the table may not be the right mechanism at all.

**To revisit (open, not decided):** where/how "Add disc" should live. One direction worth weighing when this is picked up: since the current-tag widget (Issue 1) already offers a contextual "propose add" entry point when an unknown tag is on the reader, the manual button serves the secondary case (pre-registering a tag without it physically on the reader). Could integrate the manual add affordance directly into the table itself (e.g. a trailing "+ Add disc" row) instead of a disconnected button above it — not decided, needs a proper look before committing.

**Expert-agent proposals (2026-09-02):**
- **A. Trailing ghost row** ("+ Add disc" at the bottom of the table): matches the "table-centric" instinct, but bad discoverability once the library is long (scrolled out of view), adds row height for zero data value.
- **B. Header-row action** (page title left, button right, above the table — standard admin-list convention): always visible regardless of scroll/empty state, matches this audience's expectations, smallest change.
- **C. "+" in the empty top-left/top-right header cell** (spreadsheet corner pattern): compact but low discoverability, easy to confuse with a sort/select-all control.
- **D. Fold into the current-tag widget, drop the standalone control**: rejected by the agent — overloads a live-status component with manual data entry, and the widget persists across all pages, not just Library.

**Agent's recommendation: B.** Smallest legitimate fix to the actual complaint (badly placed, not badly conceived) — keep it visually plain (same weight as Edit/Delete), not a marketing CTA.

**Decision: B, implemented (2026-09-02).** "Add disc" moved into a `.page-header` band next to the `<h2>Library</h2>` title (title left, button right), plain button styling, hidden while a create/edit form is open.

## Issue 11: No visual distinction between buttons in the disc create/edit form

**Decision:** agreed. `DiscForm.svelte`'s Save/Cancel get a primary/secondary hierarchy — `.btn-primary` (accent, filled) for Save, `.btn-secondary` (outline/ghost, low visual weight) for Cancel. Danger (`.btn-danger`) stays as-is for Delete.

## Issue 12: Responsive collapse of Type and URI columns

**Revised decision (2026-09-02), superseding the first pass:** the first implementation used a 700px breakpoint tied only to the Type column, disconnected from the table's actual overflow, and left URI never adapting at all — the whole table just scrolled horizontally instead. New approach: accept horizontal table scroll as the normal fallback in the middle range (stop fighting it column by column), and reserve special handling for one real phone-width breakpoint (480px), where both collapse together: Type drops its text label (emoji only), URI shrinks to a 3-character stub (`max-width: 3ch` on the monospace `.uri-text` — an approximation of "3 characters," not an exact-character-count truncation). Full URI value stays reachable via Edit regardless.

Also fixed in the same pass: Title had gained a `max-width: 260px` as part of the original fix, which forced long titles onto far too many wrapped lines even with room to spare — replaced with a `min-width: 180px` floor now that scroll is the accepted fallback (no ceiling needed).

## Issue 13: Minimal footer, styled after Tracksy's

**Context:** requested 2026-09-02. Reference: [Tracksy](https://github.com/Gudsfile/tracksy) (same maintainer) — `app/src/components/App.tsx`. Its footer is a single centered line at the bottom of the page: one link ("Music stats made with ❤️ & 🔐 · View on GitHub"), small/muted text, subtle hover color shift, opens the repo in a new tab (`target="_blank" rel="noopener noreferrer"`).

**Decision:** same shape for Jukebox — centered, bottom of page, small muted text (reuse `--text`), single link out to the project repo (`https://github.com/Gudsfile/jukebox`), hover state, `target="_blank" rel="noopener noreferrer"`, no other content. Proposed tagline: **"Jukebox made with ❤️ & 💿 · View on GitHub"** (💿 over 📡 — matches the disc icon already used elsewhere in this UI, Type column and tag-spin). Persistent shell element in `App.svelte` next to `nav`, not duplicated per page.

---

## Issue 14: Rethink the phone layout as a card, not a shrunk table (open, not decided)

**Context:** raised 2026-09-02 while discussing Issue 12's phone breakpoint. Even with Type-emoji-only and a 3-char URI stub, a 7-column table may just be the wrong shape at phone width. Floated idea: below a phone-width breakpoint, restructure each row as a stacked card — Title with Tag underneath it, Type (emoji only), Shuffle, and the row actions — dropping the tabular grid entirely rather than continuing to compress its columns.

**Not decided** — explicitly a "wondering out loud," not a commitment. To be scoped properly (incl. whether it's worth a distinct component vs. more table-collapse tricks) when picked up.
