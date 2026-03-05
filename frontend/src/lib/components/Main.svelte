<script lang="ts">
  import { gameLog } from '$lib/stores/gameLog.js';
  import { currentLang } from '$lib/stores/i18n.js';
  import Markdown from 'svelte-markdown';
  
  $: entries = $gameLog;
  let lang = $currentLang;
  
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
        <p class="empty-text">{t('main.awaiting')}</p>
        <p class="empty-hint">{t('main.hint')}</p>
      </div>
    {:else}
      {#each entries as entry (entry.id)}
        <div class="log-entry">
          <div class="log-timestamp">{formatTimestamp(entry.timestamp)}</div>
          <div class="log-content markdown-content">
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
    font-size: 14px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 8px;
  }
  .empty-hint {
    font-size: 12px;
    color: rgba(180, 200, 180, 0.4);
  }
  .log-entry {
    padding: 16px 0;
    border-bottom: 1px solid rgba(0, 255, 153, 0.1);
  }
  .log-timestamp {
    font-size: 11px;
    color: rgba(180, 200, 180, 0.4);
    letter-spacing: 0.1em;
    margin-bottom: 8px;
    font-family: 'JetBrains Mono', monospace;
  }
  .log-content {
    font-size: 14px;
    line-height: 1.7;
    color: rgba(180, 200, 180, 0.9);
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
    font-size: 13px;
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
