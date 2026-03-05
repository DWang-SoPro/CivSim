<script lang="ts">
  import { currentLang, toggleLanguage } from '$lib/stores/i18n.js';
  
  let lang = $currentLang;
  
  function handleToggle() {
    toggleLanguage();
  }
</script>

<button class="lang-switcher" on:click={handleToggle} title="Switch Language">
  <span class="lang-icon">⌘</span>
  <span class="lang-label">{lang === 'zh' ? '中文' : 'EN'}</span>
</button>

<style>
  .lang-switcher {
    display: flex;
    align-items: center;
    gap: 8px;
    background: transparent;
    border: 1px solid rgba(0, 255, 153, 0.15);
    color: rgba(180, 200, 180, 0.6);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    padding: 6px 12px;
    cursor: pointer;
    transition: all 0.15s ease;
    letter-spacing: 0.05em;
  }
  
  .lang-switcher:hover {
    border-color: rgba(0, 255, 153, 0.3);
    color: rgba(0, 255, 153, 0.9);
    background: rgba(0, 255, 153, 0.05);
  }
  
  .lang-icon {
    font-size: 14px;
    opacity: 0.7;
  }
  
  .lang-label {
    font-weight: 600;
  }
</style>
