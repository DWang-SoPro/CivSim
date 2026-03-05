<script lang="ts">
  import { onMount } from 'svelte';
  
  export let message = '';
  export let type: 'success' | 'error' | 'warning' | 'info' = 'info';
  export let duration = 3000;
  export let onClose: () => void = () => {};
  
  let visible = false;
  
  onMount(() => {
    visible = true;
    if (duration > 0) {
      setTimeout(() => {
        visible = false;
        setTimeout(onClose, 300);
      }, duration);
    }
  });
  
  const icons = {
    success: '✓',
    error: '✕',
    warning: '⚠',
    info: 'ℹ',
  };
  
  const colors = {
    success: 'border-green',
    error: 'border-red',
    warning: 'border-amber',
    info: 'border-blue',
  };
</script>

<div class="toast {colors[type]} {visible ? 'visible' : ''}">
  <span class="toast-icon">{icons[type]}</span>
  <span class="toast-message">{message}</span>
  <button class="toast-close" on:click={() => { visible = false; setTimeout(onClose, 300); }}>×</button>
</div>

<style>
  .toast {
    position: fixed;
    top: 20px;
    right: 20px;
    min-width: 300px;
    max-width: 500px;
    padding: 12px 16px;
    background: #1a1a1a;
    border: 1px solid;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 12px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    opacity: 0;
    transform: translateX(100%);
    transition: all 0.3s ease;
    z-index: 10000;
  }
  
  .toast.visible {
    opacity: 1;
    transform: translateX(0);
  }
  
  .toast.border-green { border-color: #00ff99; }
  .toast.border-red { border-color: #ff4444; }
  .toast.border-amber { border-color: #ffb000; }
  .toast.border-blue { border-color: #5aa8cc; }
  
  .toast-icon {
    font-size: 16px;
    font-weight: 700;
  }
  
  .toast-message {
    flex: 1;
    color: rgba(180, 200, 180, 0.9);
  }
  
  .toast-close {
    background: transparent;
    border: none;
    color: rgba(180, 200, 180, 0.5);
    font-size: 18px;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s ease;
  }
  
  .toast-close:hover {
    color: rgba(180, 200, 180, 0.9);
  }
</style>
