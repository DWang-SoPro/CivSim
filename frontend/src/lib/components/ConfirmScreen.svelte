<script lang="ts">
  import { onMount } from 'svelte';
  import { gamePhase, setPhase, selection, resetSelection } from '$lib/stores/gamePhase';
  import { setCivState } from '$lib/stores/civState';
  import { currentLang } from '$lib/stores/i18n.js';
  import { t } from '$lib/stores/i18n.js';
  import { getCivTemplate, startNewGameFromTemplate } from '$lib/tauri/api';
  import MechButton from './MechButton.svelte';
  
  $: sel = $selection;
  $: lang = $currentLang;
  let isLoading = false;
  let error: string | null = null;
  let template: any = null;
  
  onMount(async () => {
    console.log('ConfirmScreen mounted, sel:', sel);
    if (sel.eraId && sel.locationId) {
      await loadTemplate();
    }
  });
  
  async function loadTemplate() {
    isLoading = true;
    error = null;
    try {
      console.log('Loading template for era:', sel.eraId, 'location:', sel.locationId);
      template = await getCivTemplate(sel.eraId!, sel.locationId!, lang);
      console.log('Template loaded:', template);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load template';
      console.error('Failed to load template:', e);
    } finally {
      isLoading = false;
    }
  }
  
  function handleBack() {
    setPhase('location');
  }
  
  async function handleStart() {
    console.log('Starting new game...');
    isLoading = true;
    try {
      const state = await startNewGameFromTemplate(sel.eraId!, sel.locationId!, lang);
      console.log('Game started with state:', state);
      setCivState(state);
      setPhase('playing');
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to start game';
      console.error('Failed to start game:', e);
    } finally {
      isLoading = false;
    }
  }
</script>

<div class="confirm-screen">
  <div class="noise-overlay"></div>
  <div class="content">
    <div class="header">
      <button class="back-btn" on:click={handleBack}>
        <span>←</span>
        <span>{t('era.back', lang)}</span>
      </button>
      <h2 class="title">{t('confirm.title', lang)}</h2>
    </div>
    
    {#if isLoading}
      <div class="loading">LOADING...</div>
    {:else if error}
      <div class="error">{error}</div>
    {:else if template}
      <div class="civ-card">
        <h3 class="civ-name">{lang === 'zh' ? template.civ_name_zh : template.civ_name_en}</h3>
        <div class="civ-details">
          <div class="detail">
            <span class="label">ERA:</span>
            <span class="value">{template.era_id}</span>
          </div>
          <div class="detail">
            <span class="label">LOCATION:</span>
            <span class="value">{template.location_id}</span>
          </div>
          <div class="detail">
            <span class="label">POPULATION:</span>
            <span class="value">{template.initial_state?.population || 'Unknown'}</span>
          </div>
          <div class="detail">
            <span class="label">STABILITY:</span>
            <span class="value">{template.initial_state?.stability || 'Unknown'}</span>
          </div>
        </div>
      </div>
      
      <div class="footer">
        <MechButton 
          onclick={handleStart}
          disabled={isLoading}
        >
          {t('confirm.start', lang)}
        </MechButton>
      </div>
    {/if}
  </div>
</div>

<style>
  .confirm-screen {
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
    max-width: 800px; width: 100%;
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
  .loading, .error {
    display: flex; align-items: center; justify-content: center;
    height: 200px; font-size: 16px;
    color: rgba(180, 200, 180, 0.5);
  }
  .error { color: #ff4444; }
  .civ-card {
    padding: 32px;
    background: rgba(0, 255, 153, 0.05);
    border: 1px solid rgba(0, 255, 153, 0.15);
    border-radius: 8px;
  }
  .civ-name {
    font-size: 32px; font-weight: 700;
    color: #00ff99; margin-bottom: 24px;
    text-transform: uppercase; letter-spacing: 0.1em;
  }
  .civ-details {
    display: grid; grid-template-columns: repeat(2, 1fr);
    gap: 16px;
  }
  .detail {
    display: flex; flex-direction: column;
    gap: 4px;
  }
  .label {
    font-size: 10px; color: rgba(180, 200, 180, 0.5);
    text-transform: uppercase; letter-spacing: 0.1em;
  }
  .value {
    font-size: 16px; color: #00ff99;
    font-family: 'JetBrains Mono', monospace;
  }
  .footer {
    display: flex; justify-content: center;
    padding-top: 24px;
    border-top: 1px solid rgba(0, 255, 153, 0.15);
  }
</style>
