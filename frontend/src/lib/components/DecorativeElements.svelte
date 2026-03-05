<script lang="ts">
  // 面板边角装饰组件
  export let variant: 'corner' | 'divider' | 'title-bar' | 'panel-frame' = 'corner';
  export let position: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right' = 'top-left';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let title: string = '';
  
  const sizeMap = {
    sm: { corner: 12, line: 20 },
    md: { corner: 16, line: 28 },
    lg: { corner: 24, line: 40 }
  };
  
  $: dimensions = sizeMap[size];
</script>

{#if variant === 'corner'}
  <!-- 边角装饰 -->
  <div class="corner-decoration {position}" style="--corner-size: {dimensions.corner}px;">
    <svg width={dimensions.corner * 2} height={dimensions.corner * 2} viewBox="0 0 40 40" fill="none">
      {#if position === 'top-left'}
        <path d="M0 0h20v2H2v18H0z" fill="currentColor"/>
        <circle cx="4" cy="4" r="1.5" fill="currentColor"/>
      {:else if position === 'top-right'}
        <path d="M40 0H20v2h18v18h2z" fill="currentColor"/>
        <circle cx="36" cy="4" r="1.5" fill="currentColor"/>
      {:else if position === 'bottom-left'}
        <path d="M0 40h20v-2H2V20H0z" fill="currentColor"/>
        <circle cx="4" cy="36" r="1.5" fill="currentColor"/>
      {:else}
        <path d="M40 40H20v-2h18V20h2z" fill="currentColor"/>
        <circle cx="36" cy="36" r="1.5" fill="currentColor"/>
      {/if}
    </svg>
  </div>
{:else if variant === 'divider'}
  <!-- 分隔线 -->
  <div class="divider-decoration" style="--line-length: {dimensions.line}px;">
    <div class="divider-line"></div>
    <div class="divider-diamond"></div>
    <div class="divider-line"></div>
  </div>
{:else if variant === 'title-bar'}
  <!-- 标题栏装饰 -->
  <div class="title-bar-decoration">
    <div class="title-bar-left">
      <span class="title-bracket">[</span>
      <span class="title-text">{title}</span>
      <span class="title-bracket">]</span>
    </div>
    <div class="title-bar-line"></div>
    <div class="title-bar-indicators">
      <span class="indicator"></span>
      <span class="indicator"></span>
      <span class="indicator blink"></span>
    </div>
  </div>
{:else if variant === 'panel-frame'}
  <!-- 面板框架 -->
  <div class="panel-frame">
    <slot></slot>
  </div>
{/if}

<style>
  .corner-decoration {
    position: absolute;
    color: #c9a227;
    opacity: 0.7;
    pointer-events: none;
    z-index: 10;
  }
  
  .corner-decoration.top-left { top: 0; left: 0; }
  .corner-decoration.top-right { top: 0; right: 0; }
  .corner-decoration.bottom-left { bottom: 0; left: 0; }
  .corner-decoration.bottom-right { bottom: 0; right: 0; }
  
  .divider-decoration {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 8px 0;
    opacity: 0.5;
  }
  
  .divider-line {
    width: var(--line-length, 28px);
    height: 1px;
    background: linear-gradient(90deg, transparent, #5a6050, transparent);
  }
  
  .divider-diamond {
    width: 6px;
    height: 6px;
    background: #c9a227;
    transform: rotate(45deg);
  }
  
  .title-bar-decoration {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 8px 12px;
    background: linear-gradient(90deg, #0a0f0a 0%, #141f14 50%, #0a0f0a 100%);
    border-bottom: 1px solid #1a2a1a;
  }
  
  .title-bar-left {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: 'Courier Prime', monospace;
    font-size: 12px;
    color: #b8b098;
    white-space: nowrap;
  }
  
  .title-bracket {
    color: #5a6050;
  }
  
  .title-text {
    color: #c9a227;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  
  .title-bar-line {
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #1a2a1a, transparent);
  }
  
  .title-bar-indicators {
    display: flex;
    gap: 4px;
  }
  
  .indicator {
    width: 4px;
    height: 4px;
    background: #5a8a4a;
    border-radius: 50%;
  }
  
  .indicator.blink {
    animation: blink 1.5s infinite;
  }
  
  .panel-frame {
    position: relative;
    border: 1px solid #1a2a1a;
    background: linear-gradient(135deg, rgba(20, 31, 20, 0.95), rgba(10, 15, 10, 0.98));
    box-shadow: 
      inset 0 1px 0 rgba(184, 176, 152, 0.03),
      0 2px 8px rgba(0, 0, 0, 0.3);
  }
  
  .panel-frame::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(201, 162, 39, 0.3), transparent);
  }
  
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
</style>
