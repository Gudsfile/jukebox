<script>
  // PROTOTYPE, throwaway: four collapsed variants of the ReaderSlot, switchable with `?variant=`
  // on the Library page (`npm run dev`, then /ui/?variant=A). Question: what should the collapsed
  // reader widget look like? Expanded state is the real ReaderSlot, plus a collapse toggle.
  import ReaderSlot from '../ReaderSlot.svelte'
  import CollapsedSlimBar from './CollapsedSlimBar.svelte'
  import CollapsedPill from './CollapsedPill.svelte'
  import CollapsedCornerChip from './CollapsedCornerChip.svelte'
  import CollapsedDockedTab from './CollapsedDockedTab.svelte'
  import PrototypeSwitcher from './PrototypeSwitcher.svelte'
  import { READER_STATES } from './mock.js'

  let { currentTag = $bindable(null), disc, actionsEnabled, onAdd, onEdit } = $props()

  const VARIANTS = {
    A: { name: 'Slim bar', component: CollapsedSlimBar },
    B: { name: 'Pill', component: CollapsedPill },
    C: { name: 'Corner chip', component: CollapsedCornerChip },
    D: { name: 'Docked tab', component: CollapsedDockedTab },
  }

  const initial = new URLSearchParams(location.search).get('variant')
  let variant = $state(initial in VARIANTS ? initial : 'A')
  let collapsed = $state(true)
  let readerState = $state('known')

  $effect(() => {
    currentTag = READER_STATES[readerState]
  })

  function setVariant(key) {
    variant = key
    const url = new URL(location.href)
    url.searchParams.set('variant', key)
    history.replaceState(null, '', url)
  }

  const Collapsed = $derived(VARIANTS[variant].component)
</script>

{#if collapsed}
  <Collapsed {currentTag} {disc} onExpand={() => (collapsed = false)} />
{:else}
  <ReaderSlot {currentTag} {disc} {actionsEnabled} {onAdd} {onEdit} onCollapse={() => (collapsed = true)} />
{/if}

<PrototypeSwitcher
  variants={Object.fromEntries(Object.entries(VARIANTS).map(([key, v]) => [key, v.name]))}
  current={variant}
  onChange={setVariant}
  readerStates={Object.keys(READER_STATES)}
  bind:readerState
  bind:collapsed
/>
