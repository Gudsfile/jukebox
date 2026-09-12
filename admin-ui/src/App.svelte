<script>
  import CurrentTagBanner from './lib/components/CurrentTagBanner.svelte'
  import Toast from './lib/components/Toast.svelte'
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

  function goToSonos() {
    currentPage = 'sonos'
  }
</script>

<CurrentTagBanner
  onEditDisc={(tagId) => goToLibrary({ type: 'edit', tagId })}
  onAddDisc={(tagId) => goToLibrary({ type: 'create', tagId })}
/>
<Toast />

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
    <Settings onManageSpeakers={goToSonos} />
  {:else if currentPage === 'sonos'}
    <Sonos />
  {/if}
</main>

<footer>
  <a href="https://github.com/Gudsfile/jukebox" target="_blank" rel="noopener noreferrer">
    Jukebox made with ❤️ & 💿 · View on GitHub
  </a>
</footer>
