<script lang="ts">
  import { onMount } from 'svelte';
  import { gamePhase, setPhase, resetSelection } from '$lib/stores/gamePhase';
  import { currentLang } from '$lib/stores/i18n.js';
  import { t } from '$lib/stores/i18n.js';
  import { listSaves, type SaveMetadata } from '$lib/tauri/api';
  import MechButton from './MechButton.svelte';
  
  let saves: SaveMetadata[] = [];
  let isLoading = false;
  let error: string | null = null;
  let lang = $currentLang;
  $: phase = $gamePhase;
  
  onMount(async () => {
    await loadSaves();
  });
  
  async function loadSaves() {
    isLoading = true;
    error = null;
    try {
      saves = await listSaves();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load saves';
    } finally {
      isLoading = false;
    }
  }
  
  function handleNewGame() {
    resetSelection();
    setPhase('era');
  }
  
  function handleLoadGame() {
    setPhase('load');
  }
</script>

<div class="select-screen">
  <div class="noise-overlay"></div>
  <div class="content">
    <div class="title-container">
      <h1 class="title">{t('select.title', lang)}</h1>
      <p class="subtitle">{t('select.subtitle', lang)}</p>
    </div>
    
    <div class="button-group">
      <MechButton onclick={handleNewGame} disabled={isLoading}>
        <span class="button-icon">🆕</span>
        <span class="button-text">{t('select.new_game', lang)}</span>
        <span class="button-sub">{t('select.new_game_en', lang)}</span>
      </MechButton>
      
      <MechButton onclick={handleLoadGame} disabled={isLoading}>
        <span class="button-icon">📂</span>
        <span class="button-text">{t('select.load_game', lang)}</span>
        <span class="button-sub">{t('select.load_game_en', lang)}</span>
      </MechButton>
    </div>
    
    {#if error}
      <div class="error-message">
        <span>⚠️</span>
        <span>{error}</span>
      </div>
    {/if}
  </div>
  
  <div class="decorative-corners">
    <div class="corner top-left"></div>
    <div class="corner top-right"></div>
    <div class="corner bottom-left"></div>
    <div class="corner bottom-right"></div>
  </div>
</div>

<style>
  .select-screen {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: #0a0a0a;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .noise-overlay {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    opacity: 0.03;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
    pointer-events: none;
  }
  .content {
    position: relative;
    z-index: 10;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 48px;
    padding: 24px;
  }
  .title-container { text-align: center; }
  .title {
    font-size: 64px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #00ff99;
    text-shadow: 0 0 20px rgba(0, 255, 153, 0.5);
    margin: 0;
    font-family: 'JetBrains Mono', monospace;
  }
  .subtitle {
    font-size: 14px;
    letter-spacing: 0.2em;
    color: rgba(180, 200, 180, 0.5);
    margin-top: 8px;
    text-transform: uppercase;
  }
  .button-group {
    display: flex;
    flex-direction: column;
    gap: 24px;
    min-width: 400px;
  }
  .button-icon { font-size: 24px; margin-right: 12px; }
  .button-text { font-size: 16px; font-weight: 700; letter-spacing: 0.1em; }
  .button-sub {
    font-size: 10px;
    color: rgba(180, 200, 180, 0.5);
    margin-left: 36px;
  }
  .error-message {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: rgba(255, 68, 68, 0.1);
    border: 1px solid rgba(255, 68, 68, 0.3);
    border-radius: 4px;
    color: #ff4444;
    font-size: 13px;
  }
  .decorative-corners {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
  }
  .corner {
    position: absolute;
    width: 100px; height: 100px;
    border: 2px solid rgba(0, 255, 153, 0.2);
  }
  .corner.top-left { top: 20px; left: 20px; border-right: none; border-bottom: none; }
  .corner.top-right { top: 20px; right: 20px; border-left: none; border-bottom: none; }
  .corner.bottom-left { bottom: 20px; left: 20px; border-right: none; border-top: none; }
  .corner.bottom-right { bottom: 20px; right: 20px; border-left: none; border-top: none; }
</style>
