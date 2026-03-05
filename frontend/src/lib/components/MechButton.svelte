<script lang="ts">
  export let type: 'button' | 'submit' = 'button';
  export let disabled = false;
  export let loading = false;
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let variant: 'primary' | 'secondary' | 'danger' | 'success' = 'primary';
  export let onclick: () => void = () => {};
  
  const sizeClasses = {
    sm: 'px-4 py-1.5 text-xs',
    md: 'px-6 py-2 text-sm',
    lg: 'px-8 py-3 text-base'
  };
  
  const variantClasses = {
    primary: {
      base: 'bg-retro-accent border-retro-accent text-retro-bg',
      shadow: '#9a7a1a',
      hover: '#b8931f',
      active: '#8b6f18'
    },
    secondary: {
      base: 'bg-retro-bg-light border-retro-border text-retro-text',
      shadow: '#0a0f0a',
      hover: '#1f2f1f',
      active: '#151f15'
    },
    danger: {
      base: 'bg-retro-danger border-retro-danger text-retro-text',
      shadow: '#5a3010',
      hover: '#9a4a20',
      active: '#6a3515'
    },
    success: {
      base: 'bg-retro-success border-retro-success text-retro-bg',
      shadow: '#3a6a2a',
      hover: '#4a7a3a',
      active: '#2a5a1a'
    }
  };
  
  $: styles = variantClasses[variant];
  $: buttonShadow = `0 4px 0 ${styles.shadow}`;
</script>

<button
  {type}
  {disabled}
  class="mech-button relative font-retro font-bold border-2 {sizeClasses[size]} {styles.base} {disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
  style="box-shadow: {disabled ? 'none' : buttonShadow}; transform: {disabled ? 'translateY(2px)' : 'translateY(0)'};"
  on:click={() => !disabled && !loading && onclick()}
>
  <span class="mech-texture absolute inset-0 pointer-events-none opacity-20"></span>
  <span class="screw absolute top-0.5 left-0.5 w-1.5 h-1.5 rounded-full bg-black/30"></span>
  <span class="screw absolute top-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-black/30"></span>
  <span class="screw absolute bottom-0.5 left-0.5 w-1.5 h-1.5 rounded-full bg-black/30"></span>
  <span class="screw absolute bottom-0.5 right-0.5 w-1.5 h-1.5 rounded-full bg-black/30"></span>
  
  <span class="relative z-10 flex items-center justify-center gap-2">
    {#if loading}
      <span class="loading-spinner"></span>
    {/if}
    <slot />
  </span>
</button>

<style>
  .mech-button {
    transition: all 0.05s ease;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  
  .mech-button:not(:disabled):active {
    transform: translateY(3px) !important;
    box-shadow: 0 1px 0 var(--shadow-color) !important;
  }
  
  .mech-button:not(:disabled):hover {
    filter: brightness(1.1);
  }
  
  .mech-texture {
    background-image: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(0, 0, 0, 0.1) 2px,
      rgba(0, 0, 0, 0.1) 4px
    );
  }
  
  .screw::before {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 60%;
    height: 1px;
    background: rgba(0, 0, 0, 0.5);
    transform: translate(-50%, -50%) rotate(45deg);
  }
  
  .screw::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 60%;
    height: 1px;
    background: rgba(0, 0, 0, 0.5);
    transform: translate(-50%, -50%) rotate(-45deg);
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  .loading-spinner {
    display: inline-block;
    width: 0.75em;
    height: 0.75em;
    border: 2px solid currentColor;
    border-right-color: transparent;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
</style>
