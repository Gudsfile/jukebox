<script>
  import Toast from './lib/components/Toast.svelte'
  import Library from './lib/pages/Library.svelte'
  import Pn532 from './lib/pages/Pn532.svelte'
  import Settings from './lib/pages/Settings.svelte'
  import Sonos from './lib/pages/Sonos.svelte'

  const pageKeys = ['library', 'settings', 'sonos', 'pn532']
  let currentPage = $state('library')

  function goToSonos() {
    currentPage = 'sonos'
  }

  function goToPn532() {
    currentPage = 'pn532'
  }
</script>

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
    <Library />
  {:else if currentPage === 'settings'}
    <Settings onManageSpeakers={goToSonos} onConfigurePn532={goToPn532} />
  {:else if currentPage === 'sonos'}
    <Sonos />
  {:else if currentPage === 'pn532'}
    <Pn532 />
  {/if}
</main>

<footer>
  <a href="https://github.com/Gudsfile/jukebox" target="_blank" rel="noopener noreferrer">
    Jukebox made with ❤️ & 💿 · View on GitHub
  </a>
</footer>
