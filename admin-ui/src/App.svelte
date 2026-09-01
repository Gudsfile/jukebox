<script>
  import CurrentTagBanner from './lib/components/CurrentTagBanner.svelte'
  import Library from './lib/pages/Library.svelte'
  import Settings from './lib/pages/Settings.svelte'
  import Sonos from './lib/pages/Sonos.svelte'

  const pageKeys = ['library', 'settings', 'sonos']
  let currentPage = $state('library')
  let libraryIntent = $state(null)

  function goToLibrary(intent) {
    libraryIntent = intent
    currentPage = 'library'
  }

  function clearLibraryIntent() {
    libraryIntent = null
  }
</script>

<CurrentTagBanner
  onEditDisc={(tagId) => goToLibrary({ type: 'edit', tagId })}
  onAddDisc={(tagId) => goToLibrary({ type: 'create', tagId })}
/>

<nav>
  {#each pageKeys as page (page)}
    <button class:active={currentPage === page} onclick={() => (currentPage = page)}>
      {page}
    </button>
  {/each}
</nav>

<main>
  {#if currentPage === 'library'}
    <Library intent={libraryIntent} onIntentConsumed={clearLibraryIntent} />
  {:else if currentPage === 'settings'}
    <Settings />
  {:else if currentPage === 'sonos'}
    <Sonos />
  {/if}
</main>
