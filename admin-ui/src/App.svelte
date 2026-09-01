<script>
  import CurrentTagBanner from './lib/components/CurrentTagBanner.svelte'
  import Library from './lib/pages/Library.svelte'
  import Settings from './lib/pages/Settings.svelte'
  import Sonos from './lib/pages/Sonos.svelte'

  const pages = { library: Library, settings: Settings, sonos: Sonos }
  let currentPage = $state('library')
  let Page = $derived(pages[currentPage])
</script>

<CurrentTagBanner />

<nav>
  {#each Object.keys(pages) as page (page)}
    <button class:active={currentPage === page} onclick={() => (currentPage = page)}>
      {page}
    </button>
  {/each}
</nav>

<main>
  <Page />
</main>
