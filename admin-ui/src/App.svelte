<script>
  import Toast from './lib/components/Toast.svelte'
  import Library from './lib/pages/Library.svelte'
  import Settings from './lib/pages/Settings.svelte'
  import Sonos from './lib/pages/Sonos.svelte'

  const pageKeys = ['library', 'settings', 'sonos']
  let currentPage = $state('library')

  function goToSonos() {
    currentPage = 'sonos'
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
