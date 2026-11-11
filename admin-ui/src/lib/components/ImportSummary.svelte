<script>
  let { kind, summary } = $props()
</script>

{#if kind === 'library'}
  <p>The current library will be replaced by {summary.disc_count} discs.</p>
  <ul>
    {#each [['Added', summary.added], ['Changed', summary.changed], ['Removed', summary.removed]] as [label, tags] (label)}
      <li>
        {label}: {tags.length}
        {#if tags.length}<span class="path">({tags.join(', ')})</span>{/if}
      </li>
    {/each}
  </ul>
{:else}
  {#if summary.current_settings_error}
    <p class="error">The current settings file is invalid and will be replaced: {summary.current_settings_error}</p>
  {/if}
  {#if summary.updated_paths.length}
    <p>The persisted settings will be replaced. Changed settings:</p>
    <ul>
      {#each summary.updated_paths as path (path)}
        <li class="path">{path}</li>
      {/each}
    </ul>
    {#if summary.restart_required_paths.length}
      <p>Changes take effect after restart.</p>
    {/if}
  {:else}
    <p>The file holds the same settings as the current ones.</p>
  {/if}
{/if}
