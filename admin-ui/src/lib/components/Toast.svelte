<script>
  import { toastStore } from '../stores/toastStore.js'
</script>

{#if $toastStore}
  <div class="toast">
    <p>{$toastStore.message}</p>
    <button type="button" aria-label="Close toast" onclick={() => toastStore.dismiss()}> ✕ </button>
  </div>
{/if}

<style>
  .toast {
    position: fixed;
    bottom: 1rem;
    right: 1rem;
    background-color: var(--success);
    color: var(--success-text);
    padding: 1rem;
    border-radius: 0.5rem;
    display: flex;
    align-items: center;
    gap: 1rem;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    animation: slideIn 0.3s ease-out;
    z-index: 1000;
  }

  @keyframes slideIn {
    from {
      transform: translateX(400px);
      opacity: 0;
    }
    to {
      transform: translateX(0);
      opacity: 1;
    }
  }

  .toast p {
    margin: 0;
  }

  .toast button {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--success-text);
    font-size: 1rem;
    padding: 0;
    line-height: 1;
  }

  .toast button:hover {
    opacity: 0.7;
  }
</style>
