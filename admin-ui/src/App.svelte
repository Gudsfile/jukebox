<script>
  import { onMount } from 'svelte'
  import { apiGet } from './lib/api.js'
  import Toast from './lib/components/Toast.svelte'
  import Library from './lib/pages/Library.svelte'
  import Pn532 from './lib/pages/Pn532.svelte'
  import Settings from './lib/pages/Settings.svelte'
  import Sonos from './lib/pages/Sonos.svelte'

  const pageKeys = ['library', 'settings', 'sonos', 'pn532']
  let currentPage = $state('library')

  let version = $state(null)

  // The footer is secondary: a failed request only hides the version, without a toast.
  onMount(async () => {
    try {
      version = (await apiGet('/version')).version ?? null
    } catch {
      // keep the footer without a version
    }
  })

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
  Jukebox
  {#if version === 'unknown'}
    {version} •
  {:else if version}
    <a href={`https://github.com/Gudsfile/jukebox/releases/tag/v${version}`} target="_blank" rel="noopener noreferrer"
      >v{version}</a
    > •
  {/if}
  made with ❤️ & 💿 •
  <a href="https://github.com/Gudsfile/jukebox" target="_blank" rel="noopener noreferrer">view on GitHub</a>
</footer>
