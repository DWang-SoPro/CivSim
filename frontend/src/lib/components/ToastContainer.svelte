<script lang="ts">
  import Toast from './Toast.svelte';
  import { toast } from '$lib/stores/toast';
  
  $: toasts = $toast;
  
  function handleClose(id: string) {
    toast.removeToast(id);
  }
</script>

<div class="toast-container">
  {#each toasts as t (t.id)}
    <Toast
      message={t.message}
      type={t.type}
      duration={t.duration}
      onClose={() => handleClose(t.id)}
    />
  {/each}
</div>

<style>
  .toast-container {
    position: fixed;
    top: 0;
    right: 0;
    z-index: 10000;
    pointer-events: none;
  }
  
  .toast-container > * {
    pointer-events: auto;
  }
</style>
