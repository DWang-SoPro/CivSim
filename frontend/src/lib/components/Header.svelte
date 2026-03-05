<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { currentLang } from '$lib/stores/i18n.js';
  import LanguageSwitcher from './LanguageSwitcher.svelte';
  import { civState } from '$lib/stores/civState.js';
  import { setPhase } from '$lib/stores/gamePhase.js';
  const dispatch = createEventDispatcher();
  
  $: state = $civState;
  $: lang = $currentLang;
  let lang = $currentLang;
  
  const t = (key: string) => {
    const translations: Record<string, Record<string, string>> = {
      zh: {
        year: '年份',
        civilization: '文明',
        stability: '稳定性',
        authority: '统治力',
        save: '保存',
        load: '加载',
      },
      en: {
        year: 'YEAR',
        civilization: 'CIVILIZATION',
        stability: 'STABILITY',
        authority: 'AUTHORITY',
        save: 'SAVE',
        load: 'LOAD',
      }
    };
    return translations[lang][key] || key;
  };
  
  function handleSave() {
    dispatch('saveGame');
  }
  
  function handleLoad() {
    dispatch('loadGame');
  }
  
  function handleBackToHome() {
    setPhase('select');
  }
  
</script>
  
<header class="header">
  <div class="header-content">
    <button class="header-btn back-btn" on:click={handleBackToHome}>
      <span class="btn-icon">←</span>
      <span class="btn-text">{lang === 'zh' ? '主页' : 'HOME'}</span>
    </button>
    
    <div class="divider"></div>
    
    <div class="stat-item">
      <span class="stat-label">{t('year')}</span>
      <span class="stat-value">
        {#if state.year > 0}
          {state.year}
        {:else}
          -{Math.abs(state.year)}
        {/if}
      </span>
    </div>
    
    <div class="divider"></div>
    
    <div class="stat-item">
      <span class="stat-label">{t('civilization')}</span>
      <span class="stat-value text-amber">{state.civ_name}</span>
    </div>
    
    <div class="divider"></div>
    
    <div class="stat-item">
      <span class="stat-label">{t('stability')}</span>
      <span class="stat-value {state.stability < 50 ? 'text-red' : 'text-green'}">{state.stability}</span>
    </div>
    
    <div class="divider"></div>
    
    <div class="stat-item">
      <span class="stat-label">{t('authority')}</span>
      <span class="stat-value text-amber">{state.authority}</span>
    </div>
    
    <div class="spacer"></div>
    
    <button class="header-btn" on:click={handleSave}>
      <span class="btn-icon">💾</span>
      <span class="btn-text">{t('save')}</span>
    </button>
    
    <button class="header-btn" on:click={handleLoad}>
      <span class="btn-icon">📂</span>
      <span class="btn-text">{t('load')}</span>
    </button>
    
    <LanguageSwitcher />
  </div>
</header>

<style>
  .header {
    height: 48px;
    background: #0f0f0f;
    border-bottom: 1px solid rgba(0, 255, 153, 0.15);
    display: flex;
    align-items: center;
    padding: 0 24px;
    flex-shrink: 0;
  }
  .header-content {
    display: flex;
    align-items: center;
    gap: 24px;
    width: 100%;
  }
  .stat-item {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .stat-label {
    font-size: 11px;
    letter-spacing: 0.1em;
    color: rgba(180, 200, 180, 0.5);
    text-transform: uppercase;
  }
  .stat-value {
    font-size: 13px;
    font-weight: 600;
    color: rgba(180, 200, 180, 0.9);
    font-family: 'JetBrains Mono', monospace;
  }
  .divider {
    width: 1px;
    height: 16px;
    background: rgba(0, 255, 153, 0.15);
  }
  .spacer { flex: 1; }
  .header-btn {
    display: flex;
    align-items: center;
    gap: 6px;
    background: #1a1a1a;
    border: 1px solid rgba(0, 255, 153, 0.15);
    padding: 6px 12px;
    border-radius: 2px;
    cursor: pointer;
    transition: all 0.15s ease;
    color: rgba(180, 200, 180, 0.9);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .header-btn:hover {
    border-color: #00ff99;
    color: #00ff99;
    background: rgba(0, 255, 153, 0.05);
  }
  .header-btn:active {
    transform: translateY(1px);
  }
  .btn-icon { font-size: 14px; }
  .text-green { color: #00ff99; }
  .text-amber { color: #ffb000; }
  .text-red { color: #ff4444; }
</style>
