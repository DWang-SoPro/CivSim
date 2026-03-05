<script lang="ts">
  import DecorativeElements from './DecorativeElements.svelte';
  
  export let title: string = '';
  export let variant: 'default' | 'minimal' | 'bordered' = 'default';
  export let className: string = '';
</script>

{#if variant === 'default'}
  <div class="panel-decor relative {className}">
    <!-- 四个角装饰 -->
    <div class="absolute top-0 left-0 z-10">
      <DecorativeElements variant="corner" position="top-left" size="sm" />
    </div>
    <div class="absolute top-0 right-0 z-10">
      <DecorativeElements variant="corner" position="top-right" size="sm" />
    </div>
    <div class="absolute bottom-0 left-0 z-10">
      <DecorativeElements variant="corner" position="bottom-left" size="sm" />
    </div>
    <div class="absolute bottom-0 right-0 z-10">
      <DecorativeElements variant="corner" position="bottom-right" size="sm" />
    </div>
    
    <!-- 标题栏 -->
    {#if title}
      <DecorativeElements variant="title-bar" {title} />
    {/if}
    
    <!-- 内容 -->
    <div class="panel-content">
      <slot />
    </div>
  </div>
{:else if variant === 'minimal'}
  <div class="panel-minimal {className}">
    <div class="flex items-center justify-between px-4 py-2 border-b border-retro-border bg-retro-bg-light">
      <h3 class="text-retro-accent text-xs font-bold tracking-wider">{title}</h3>
      <div class="flex gap-1">
        <div class="w-2 h-2 rounded-full bg-retro-dim/30"></div>
        <div class="w-2 h-2 rounded-full bg-retro-dim/30"></div>
      </div>
    </div>
    <slot />
  </div>
{:else if variant === 'bordered'}
  <div class="panel-bordered relative {className}">
    {#if title}
      <DecorativeElements variant="title-bar" {title} />
    {/if}
    <slot />
  </div>
{/if}

<style>
  .panel-decor {
    background: linear-gradient(135deg, rgba(20, 31, 20, 0.95) 0%, rgba(10, 15, 10, 0.98) 100%);
    border: 1px solid #1a2a1a;
    padding: 16px;
    margin: 8px 0;
  }

  .panel-content {
    position: relative;
    z-index: 1;
  }

  .panel-minimal {
    background: rgba(10, 15, 10, 0.6);
    border: 1px solid #1a2a1a;
    border-radius: 2px;
  }

  .panel-bordered {
    border: 1px solid #2a3a2a;
    padding: 12px;
  }

  .panel-bordered::before {
    content: '';
    position: absolute;
    top: -1px;
    left: -1px;
    right: -1px;
    bottom: -1px;
    border: 1px solid transparent;
    border-image: linear-gradient(135deg, #d4af37 0%, transparent 30%, transparent 70%, #d4af37 100%) 1;
    pointer-events: none;
  }
</style>
