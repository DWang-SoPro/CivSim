<script lang="ts">
  import { onMount } from 'svelte';
  import { gamePhase, setPhase, selectLocation, selection } from '$lib/stores/gamePhase';
  import { currentLang } from '$lib/stores/i18n.js';
  import { t } from '$lib/stores/i18n.js';
  import { listLocations, hasCivTemplate, type Location } from '$lib/tauri/api';
  import MechButton from './MechButton.svelte';
  
  let locations: Location[] = [];
  let availableLocations: string[] = [];
  let isLoading = false;
  let error: string | null = null;
  let selectedLocationId: string | null = null;
  $: lang = $currentLang;
  $: sel = $selection;
  
  onMount(async () => {
    console.log('LocationSelector mounted, sel.eraId:', sel.eraId);
    await loadLocations();
  });
  
  async function loadLocations() {
    isLoading = true;
    error = null;
    try {
      locations = await listLocations();
      console.log('Locations loaded:', locations);
      console.log('Current eraId:', sel.eraId);
      
      if (sel.eraId) {
        const results = await Promise.all(
          locations.map(async loc => {
            try {
              const has = await hasCivTemplate(sel.eraId!, loc.id);
              return has ? loc.id : null;
            } catch (e) {
              console.error(`hasCivTemplate failed for ${loc.id}:`, e);
              return null;
            }
          })
        );
        availableLocations = results.filter(Boolean) as string[];
        console.log('Available locations:', availableLocations);
      } else {
        availableLocations = locations.map(l => l.id);
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load locations';
      console.error('Failed to load locations:', e);
    } finally {
      isLoading = false;
    }
  }
  
  function handleSelect(locationId: string) {
    selectedLocationId = locationId;
    selectLocation(locationId);
    console.log('Location selected:', locationId);
  }
  
  function handleBack() {
    setPhase('era');
  }
  
  function handleContinue() {
    console.log('handleContinue, selectedLocationId:', selectedLocationId);
    if (selectedLocationId) {
      setPhase('confirm');
    }
  }
  
  function getLocationName(loc: Location): string {
    const key = `location.${loc.id}`;
    const translated = t(key, lang);
    return translated === key ? (lang === 'zh' ? loc.display_name_zh : loc.display_name_en) : translated;
  }
  
  function isAvailable(locationId: string): boolean {
    return availableLocations.includes(locationId);
  }
</script>

<div class="location-selector">
  <div class="noise-overlay"></div>
  <div class="content">
    <div class="header">
      <button class="back-btn" on:click={handleBack}>
        <span>←</span>
        <span>{t('era.back', lang)}</span>
      </button>
      <h2 class="title">{t('location.select', lang)}</h2>
    </div>
    
    <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;background:rgba(0,255,153,0.05);border:1px solid rgba(0,255,153,0.15);border-radius:4px;margin-bottom:16px;">
      <span style="font-size:18px;">📍</span>
      <span style="font-size:13px;color:rgba(0,255,153,0.7);font-family:'JetBrains Mono',monospace;line-height:1.5;">
        {lang === 'zh' 
          ? '灰色地点表示当前时代无史实文明。仅显示 6 个预设文明模板。' 
          : 'Gray locations have no historical civilization for this era. 6 preset templates only.'}
      </span>
    </div>

    <div class="locations-grid">
      {#if isLoading}
        <div class="loading">LOADING...</div>
      {:else if error}
        <div class="error">{error}</div>
      {:else}
        {#each locations as location}
          <div 
            class="location-card {selectedLocationId === location.id ? 'selected' : ''} {!isAvailable(location.id) ? 'unavailable' : ''}"
            on:click={() => isAvailable(location.id) && handleSelect(location.id)}
          >
            <div class="loc-name">{getLocationName(location)}</div>
            <div class="loc-fertility">
              Fertility: {(location.biome_fertility * 100).toFixed(0)}%
            </div>
            {#if !isAvailable(location.id)}
              <div class="unavailable-badge">Limited Data</div>
            {/if}
            <div class="loc-indicator"></div>
          </div>
        {/each}
      {/if}
    </div>
    
    <div class="footer">
      <MechButton 
        onclick={handleContinue}
        disabled={!selectedLocationId || isLoading}
      >
        {t('confirm.title', lang)} →
      </MechButton>
    </div>
  </div>
</div>

<style>
  .location-selector {
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
  .info-banner {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 16px;
    background: rgba(0, 255, 153, 0.05);
    border: 1px solid rgba(0, 255, 153, 0.15);
    border-radius: 4px;
  }
  .info-icon { font-size: 18px; }
  .info-text {
    font-size: 13px;
    color: rgba(0, 255, 153, 0.7);
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.5;
  }
  .locations-grid {
    font-size: 24px; font-weight: 700;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: rgba(180, 200, 180, 0.8); margin: 0;
  }
  .locations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 24px; flex: 1;
  }
  .location-card {
    position: relative; padding: 24px;
    background: rgba(0, 255, 153, 0.03);
    border: 1px solid rgba(0, 255, 153, 0.1);
    border-radius: 8px; cursor: pointer;
    transition: all 0.3s;
  }
  .location-card:hover:not(.unavailable) {
    background: rgba(0, 255, 153, 0.06);
    border-color: rgba(0, 255, 153, 0.3);
    transform: translateY(-2px);
  }
  .location-card.selected {
    background: rgba(0, 255, 153, 0.08);
    border-color: #00ff99;
    box-shadow: 0 0 20px rgba(0, 255, 153, 0.2);
  }
  .location-card.unavailable { opacity: 0.5; cursor: not-allowed; }
  .loc-name {
    font-size: 18px; font-weight: 700;
    color: #00ff99; margin-bottom: 12px;
  }
  .loc-fertility {
    font-size: 12px;
    color: rgba(180, 200, 180, 0.6);
    font-family: 'JetBrains Mono', monospace;
  }
  .unavailable-badge {
    position: absolute; top: 12px; right: 12px;
    padding: 4px 8px;
    background: rgba(255, 176, 0, 0.2);
    border: 1px solid rgba(255, 176, 0, 0.4);
    border-radius: 4px;
    color: #ffb000;
    font-size: 10px; text-transform: uppercase;
  }
  .loc-indicator {
    position: absolute; top: 12px; right: 12px;
    width: 16px; height: 16px; border-radius: 50%;
    border: 2px solid rgba(0, 255, 153, 0.3);
  }
  .location-card.selected .loc-indicator {
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
