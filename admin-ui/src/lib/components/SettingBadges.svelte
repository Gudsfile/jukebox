<script>
  let { setting } = $props()
</script>

{#if setting.is_persisted}<span class="badge badge-configured">Configured</span>{/if}
{#if setting.is_pinned_default}<span class="badge badge-pinned">Pinned default</span>{/if}
{#if setting.requires_restart}<span class="badge badge-restart">Restart required</span>{/if}
{#if setting.advanced}<span class="badge badge-advanced">Advanced</span>{/if}
