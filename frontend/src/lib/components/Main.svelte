<script lang="ts">
  import { gameLog } from '$lib/stores/gameLog.js';
  import { currentLang } from '$lib/stores/i18n.js';
  import Markdown from 'svelte-markdown';
  import { onMount, onDestroy } from 'svelte';
  
  $: entries = $gameLog;
  let lang = $currentLang;
  
  // 响应式字体大小
  let fontSize = 14;
  let lineHeight = 1.7;
  
  function calculateResponsiveFontSize() {
    const width = window.innerWidth;
    const height = window.innerHeight;
    
    // 基于窗口宽度计算字体大小
    if (width >= 1920) {
      fontSize = 16;
      lineHeight = 1.8;
    } else if (width >= 1440) {
      fontSize = 15;
      lineHeight = 1.75;
    } else if (width >= 1024) {
      fontSize = 14;
      lineHeight = 1.7;
    } else {
      fontSize = 13;
      lineHeight = 1.6;
    }
    
    // 如果是大屏但高度较小（如超宽屏），适当调整
    if (width >= 1920 && height < 900) {
      fontSize = 15;
    }
  }
  
  onMount(() => {
    calculateResponsiveFontSize();
    window.addEventListener('resize', calculateResponsiveFontSize);
  });
  
  onDestroy(() => {
    window.removeEventListener('resize', calculateResponsiveFontSize);
  });
  
  const t = (key: string) => {
    const translations: Record<string, Record<string, string>> = {
      zh: {
        'main.awaiting': '等待指令中...',
        'main.hint': '请在下方输入您的文明敕令',
      },
      en: {
        'main.awaiting': 'Awaiting input...',
        'main.hint': 'Enter your civilization decree below',
      }
    };
    return translations[lang][key] || key;
  };
  
  function formatTimestamp(ts: string): string {
    const date = new Date(ts);
    return date.toLocaleTimeString(lang === 'zh' ? 'zh-CN' : 'en-US', { hour12: false });
  }
</script>

<main class="main-display">
  <div class="log-container">
    {#if entries.length === 0}
      <div class="empty-state">
        <div class="empty-icon">⌨</div>
        <p class="empty-text" style="font-size: {fontSize + 2}px;">{t('main.awaiting')}</p>
        <p class="empty-hint" style="font-size: {fontSize - 2}px;">{t('main.hint')}</p>
      </div>
    {:else}
      {#each entries as entry (entry.id)}
        <div class="log-entry">
          <div class="log-timestamp" style="font-size: {fontSize - 3}px;">{formatTimestamp(entry.timestamp)}</div>
          <div class="log-content markdown-content" style="font-size: {fontSize}px; line-height: {lineHeight};">
            <Markdown source={entry.message} />
          </div>
        </div>
      {/each}
    {/if}
  </div>
</main>

<style>
  .main-display {
    flex: 1;
    background: #0a0a0a;
    overflow-y: auto;
    padding: 0;
    min-width: 0;
  }
  .log-container {
    padding: 24px;
    max-width: 900px;
    margin: 0 auto;
  }
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 400px;
    color: rgba(180, 200, 180, 0.5);
  }
  .empty-icon { font-size: 48px; margin-bottom: 16px; opacity: 0.3; }
  .empty-text {
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .empty-hint {
    color: rgba(180, 200, 180, 0.4);
  }
  .log-entry {
    padding: 16px 0;
    border-bottom: 1px solid rgba(0, 255, 153, 0.1);
  }
  .log-timestamp {
    color: rgba(180, 200, 180, 0.4);
    letter-spacing: 0.1em;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
  }
  .log-content {
    color: rgba(180, 200, 180, 0.9);
    transition: font-size 0.2s ease;
  }
  .markdown-content :global(p) {
    margin: 8px 0;
  }
  .markdown-content :global(strong) {
    color: #00ff99;
  }
  .markdown-content :global(em) {
    color: rgba(180, 200, 180, 0.7);
  }
  .markdown-content :global(ul), .markdown-content :global(ol) {
    padding-left: 20px;
    margin: 8px 0;
  }
  .markdown-content :global(li) {
    margin: 4px 0;
  }
  .markdown-content :global(blockquote) {
    border-left: 3px solid rgba(0, 255, 153, 0.3);
    padding-left: 16px;
    margin: 8px 0;
    color: rgba(180, 200, 180, 0.7);
  }
  .markdown-content :global(code) {
    background: rgba(0, 255, 153, 0.05);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: 'JetBrains Mono', monospace;
    color: #00ff99;
  }
  .markdown-content :global(pre) {
    background: rgba(0, 255, 153, 0.05);
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 8px 0;
  }
  .markdown-content :global(pre code) {
    background: transparent;
    padding: 0;
  }
</style>
