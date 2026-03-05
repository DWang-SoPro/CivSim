<script lang="ts">
  import { onMount } from 'svelte';
  import { gamePhase, setPhase, selectEra, selection } from '$lib/stores/gamePhase';
  import { currentLang } from '$lib/stores/i18n.js';
  import { t } from '$lib/stores/i18n.js';
  import { listEras, type Era } from '$lib/tauri/api';
  import MechButton from './MechButton.svelte';
  
  let eras: Era[] = [];
  let isLoading = false;
  let error: string | null = null;
  let selectedEraId: string | null = null;
  $: lang = $currentLang;
  $: sel = $selection;
  
  onMount(async () => {
    await loadEras();
  });
  
  async function loadEras() {
    isLoading = true;
    error = null;
    try {
      eras = await listEras();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load eras';
      console.error('Failed to load eras:', e);
    } finally {
      isLoading = false;
    }
  }
  
  function handleSelect(eraId: string) {
    selectedEraId = eraId;
    selectEra(eraId);
    console.log('Era selected:', eraId);
  }
  
  function handleBack() {
    setPhase('select');
  }
  
  function handleContinue() {
    console.log('handleContinue called, selectedEraId:', selectedEraId);
    if (selectedEraId) {
      console.log('Setting phase to location');
      setPhase('location');
    } else {
      console.log('No era selected!');
    }
  }
  
  function getEraDisplayName(era: Era): string {
    const key = `era.${era.id}`;
    const translated = t(key, lang);
    return translated === key ? (lang === 'zh' ? era.display_name_zh : era.display_name_en) : translated;
  }
  
  function getEraDescription(era: Era): string {
    return lang === 'zh' ? era.description_zh : era.description_en;
  }
</script>

<div class="era-selector">
  <div class="noise-overlay"></div>
  <div class="content">
    <div class="header">
      <button class="back-btn" on:click={handleBack}>
        <span>←</span>
        <span>{t('era.back', lang)}</span>
      </button>
      <h2 class="title">{t('era.select', lang)}</h2>
    </div>
    
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:rgba(0,255,153,0.05);border:1px solid rgba(0,255,153,0.15);border-radius:4px;margin-bottom:16px;">
      <span style="font-size:18px;">ℹ️</span>
      <span style="font-size:13px;color:rgba(0,255,153,0.7);font-family:'JetBrains Mono',monospace;line-height:1.5;">
        {lang === 'zh' 
          ? '仅显示史实文明组合，保证历史准确性。共 6 个预设文明模板。' 
          : 'Showing historically accurate civilizations. 6 preset templates available.'}
      </span>
    </div>
    

    <div class="eras-grid">
      {#if isLoading}
        <div class="loading">LOADING...</div>
      {:else if error}
        <div class="error">{error}</div>
      {:else}
        {#each eras as era}
          <div 
            class="era-card {selectedEraId === era.id ? 'selected' : ''}"
            on:click={() => handleSelect(era.id)}
          >
            <div class="era-year">
              {era.year < 0 ? `${Math.abs(era.year)} BCE` : `${era.year} CE`}
            </div>
            <div class="era-name">{getEraDisplayName(era)}</div>
            <div class="era-desc">{getEraDescription(era)}</div>
            <div class="era-indicator"></div>
          </div>
        {/each}
      {/if}
    </div>
    
    <div class="footer">
      <MechButton 
        onclick={handleContinue}
        disabled={!selectedEraId || isLoading}
      >
        {t('location.select', lang)} →
      </MechButton>
    </div>
  </div>
</div>

<style>
  .era-selector {
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
    position: relative; z-index: 10;
    display: flex; flex-direction: column;
    gap: 32px; padding: 48px;
    max-width: 1200px; width: 100%;
  }
  .header {
    display: flex; align-items: center; gap: 24px;
    border-bottom: 1px solid rgba(0, 255, 153, 0.15);
    padding-bottom: 24px;
  }
  .back-btn {
    display: flex; align-items: center; gap: 8px;
    padding: 8px 16px; background: transparent;
    border: 1px solid rgba(0, 255, 153, 0.3);
    border-radius: 4px;
    color: rgba(180, 200, 180, 0.7);
    font-size: 12px; cursor: pointer;
    transition: all 0.2s;
  }
  .back-btn:hover { background: rgba(0, 255, 153, 0.1); color: #00ff99; }
  .title {
    font-size: 24px; font-weight: 700;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: rgba(180, 200, 180, 0.8); margin: 0;
  }
  .eras-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 24px; flex: 1;
  }
  .era-card {
    position: relative; padding: 24px;
    background: rgba(0, 255, 153, 0.03);
    border: 1px solid rgba(0, 255, 153, 0.1);
    border-radius: 8px; cursor: pointer;
    transition: all 0.3s;
  }
  .era-card:hover {
    background: rgba(0, 255, 153, 0.06);
    border-color: rgba(0, 255, 153, 0.3);
    transform: translateY(-2px);
  }
  .era-card.selected {
    background: rgba(0, 255, 153, 0.08);
    border-color: #00ff99;
    box-shadow: 0 0 20px rgba(0, 255, 153, 0.2);
  }
  .era-year {
    font-size: 14px; color: #ffb000;
    font-family: 'JetBrains Mono', monospace;
    margin-bottom: 8px;
  }
  .era-name {
    font-size: 18px; font-weight: 700;
    color: #00ff99; margin-bottom: 12px;
  }
  .era-desc {
    font-size: 12px; color: rgba(180, 200, 180, 0.6);
    line-height: 1.6;
  }
  .era-indicator {
    position: absolute; top: 12px; right: 12px;
    width: 16px; height: 16px; border-radius: 50%;
    border: 2px solid rgba(0, 255, 153, 0.3);
  }
  .era-card.selected .era-indicator {
    background: #00ff99; border-color: #00ff99;
    box-shadow: 0 0 10px rgba(0, 255, 153, 0.5);
  }
  .footer {
    display: flex; justify-content: center;
    padding-top: 24px;
    border-top: 1px solid rgba(0, 255, 153, 0.15);
  }
  .loading, .error {
    display: flex; align-items: center; justify-content: center;
    height: 200px; font-size: 16px;
    color: rgba(180, 200, 180, 0.5);
  }
  .error { color: #ff4444; }
</style>
