<script lang="ts">
  import Header from '$lib/components/Header.svelte';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Main from '$lib/components/Main.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import SelectScreen from '$lib/components/SelectScreen.svelte';
  import EraSelector from '$lib/components/EraSelector.svelte';
  import LocationSelector from '$lib/components/LocationSelector.svelte';
  import ConfirmScreen from '$lib/components/ConfirmScreen.svelte';
  import SaveLoadScreen from '$lib/components/SaveLoadScreen.svelte';
  import SaveModal from '$lib/components/SaveModal.svelte';
  import { listSaves, type SaveMetadata } from '$lib/tauri/api';
  import { toast } from '$lib/stores/toast';
  import { civState, type CivState } from '$lib/stores/civState';
  import { currentLang } from '$lib/stores/i18n.js';
  import { gamePhase, setPhase, type GamePhase } from '$lib/stores/gamePhase';
  import ToastContainer from '$lib/components/ToastContainer.svelte';
  
  $: phase = $gamePhase as GamePhase;
  $: state = $civState as CivState;
  $: lang = $currentLang;
  
  let phase = $gamePhase as GamePhase;
  let state = $civState as CivState;
  let lang = $currentLang;
  
  let showSaveModal = false;
  let existingSaves: SaveMetadata[] = [];
  let currentSaveId: number | null = null;
  
  function handleSaveGame() {
    showSaveModal = true;
    loadSavesForModal();
  }
  
  async function loadSavesForModal() {
    try {
      existingSaves = await listSaves();
    } catch (e) {
      console.error('Failed to load saves:', e);
    }
  }
  
  function handleModalClose() {
    showSaveModal = false;
  }
</script>

{#if phase === 'playing'}
  <div class="app-container">
    <ToastContainer />
    <Header 
      year={state.year}
      civName={state.civ_name}
      stability={state.stability}
      authority={state.authority}
      on:saveGame={handleSaveGame}
      on:loadGame={() => setPhase('load')}
    />
    <div class="content-area">
      <Sidebar />
      <Main />
    </div>
    <Footer on:submit={(e) => console.log('Submit:', e.detail.text)} />
  </div>
{:else if phase === 'select'}
  <SelectScreen />
{:else if phase === 'era'}
  <EraSelector />
{:else if phase === 'location'}
  <LocationSelector />
{:else if phase === 'confirm'}
  <ConfirmScreen />
{:else if phase === 'load'}
  <SaveLoadScreen />
{:else}
  <div class="placeholder-screen">
    <h2>{phase.toUpperCase()} SCREEN</h2>
    <p>To be implemented...</p>
  </div>
{/if}

{#if showSaveModal}
  <SaveModal 
    existingSaves={existingSaves}
    currentSaveId={currentSaveId}
    onClose={handleModalClose}
  />
{/if}

<style>
  :global(body) { margin: 0; padding: 0; height: 100vh; width: 100vw; overflow: hidden; }
  .app-container { display: flex; flex-direction: column; height: 100vh; width: 100vw; background: #0a0a0a; }
  .content-area { flex: 1; display: flex; overflow: hidden; }
  .placeholder-screen h2 { font-size: 24px; letter-spacing: 0.15em; margin-bottom: 16px; }
</style>
