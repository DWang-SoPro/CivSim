<script lang="ts">
  import { onMount } from 'svelte';
  import { gamePhase, setPhase } from '$lib/stores/gamePhase';
  import { currentLang } from '$lib/stores/i18n.js';
  import { t } from '$lib/stores/i18n.js';
  import { listSaves, loadGame, deleteSave, type SaveMetadata } from '$lib/tauri/api';
  import { toast } from '$lib/stores/toast';
  import { civState, setCivState } from '$lib/stores/civState.js';
  import MechButton from './MechButton.svelte';
  import LoadingSpinner from './LoadingSpinner.svelte';
  
  let saves: SaveMetadata[] = [];
  let isLoading = false;
  let isDeleting = false;
  let error: string | null = null;
  let lang = $currentLang;
  let deleteConfirmId: number | null = null;
  
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
      console.error('Failed to load saves:', e);
    } finally {
      isLoading = false;
    }
  }
  
  async function handleLoad(save: SaveMetadata) {
    if (isDeleting) return;
    
    isLoading = true;
    try {
      const newState = await loadGame(save.id);
      setCivState(newState);
      toast.success(lang === 'zh' ? '存档已加载' : 'Save loaded', 3000);
      setPhase('playing');
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      toast.error((lang === 'zh' ? '加载失败：' : 'Failed to load: ') + errorMsg, 5000);
      console.error('Failed to load save:', e);
    } finally {
      isLoading = false;
    }
  }
  
  async function handleDelete(id: number) {
    if (deleteConfirmId !== id) {
      deleteConfirmId = id;
      return;
    }
    
    isDeleting = true;
    try {
      await deleteSave(id);
      toast.success(lang === 'zh' ? '存档已删除' : 'Save deleted', 3000);
      await loadSaves();
      deleteConfirmId = null;
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      toast.error((lang === 'zh' ? '删除失败：' : 'Failed to delete: ') + errorMsg, 5000);
      console.error('Failed to delete save:', e);
    } finally {
      isDeleting = false;
    }
  }
  
  function handleBack() {
    setPhase('select');
  }
  
  function formatDate(dateStr: string): string {
    const date = new Date(dateStr);
    return date.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
  
  const emptyText = lang === 'zh' 
    ? '暂无存档。开始新游戏后，你可以在游戏中保存进度。'
    : 'No saves yet. Start a new game and save your progress in-game.';
</script>

<div class="save-load-screen">
  <div class="noise-overlay"></div>
  <div class="content">
    <div class="title-container">
      <h1 class="title">{t('save.title', lang)}</h1>
      <p class="subtitle">{t('save.select', lang)}</p>
    </div>
    
    <div class="saves-container">
      {#if isLoading && saves.length === 0}
        <div class="loading-state">
          <LoadingSpinner size={32} />
          <p>{lang === 'zh' ? '加载中...' : 'Loading...'}</p>
        </div>
      {:else if saves.length === 0}
        <div class="empty-state">
          <div class="empty-icon">📦</div>
          <p class="empty-text">{emptyText}</p>
        </div>
      {:else}
        <div class="saves-list">
          {#each saves as save (save.id)}
            <div class="save-card {deleteConfirmId === save.id ? 'confirm-delete' : ''}">
              <div class="save-info">
                <div class="save-name">{save.name}</div>
                <div class="save-date">
                  {lang === 'zh' ? '保存于：' : 'Saved: '}{formatDate(save.updated_at)}
                </div>
              </div>
              <div class="save-actions">
                <button
                  class="action-btn load-btn"
                  on:click={() => handleLoad(save)}
                  disabled={isLoading || isDeleting}
                >
                  {lang === 'zh' ? '加载' : 'LOAD'}
                </button>
                <button
                  class="action-btn delete-btn {deleteConfirmId === save.id ? 'confirming' : ''}"
                  on:click={() => handleDelete(save.id)}
                  disabled={isLoading || isDeleting}
                >
                  {deleteConfirmId === save.id 
                    ? (lang === 'zh' ? '确认删除' : 'CONFIRM') 
                    : '🗑'}
                </button>
              </div>
            </div>
          {/each}
        </div>
      {/if}
    </div>
    
    <div class="button-group">
      <MechButton onclick={handleBack}>
        <span class="button-icon">←</span>
        <span class="button-text">{t('era.back', lang)}</span>
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
  .save-load-screen {
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
    gap: 32px;
    padding: 24px;
    max-width: 800px;
    width: 100%;
  }
  .title-container { text-align: center; }
  .title {
    font-size: 48px;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #00ff99;
    text-shadow: 0 0 20px rgba(0, 255, 153, 0.5);
    margin: 0;
    font-family: 'JetBrains Mono', monospace;
  }
  .subtitle {
    font-size: 12px;
    letter-spacing: 0.2em;
    color: rgba(180, 200, 180, 0.5);
    margin-top: 8px;
    text-transform: uppercase;
  }
  .saves-container {
    width: 100%;
    max-height: 400px;
    overflow-y: auto;
  }
  .loading-state, .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
    color: rgba(180, 200, 180, 0.5);
    gap: 16px;
  }
  .empty-icon { font-size: 48px; opacity: 0.3; }
  .empty-text {
    font-size: 14px;
    letter-spacing: 0.05em;
  }
  .saves-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .save-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: rgba(0, 255, 153, 0.05);
    border: 1px solid rgba(0, 255, 153, 0.1);
    border-radius: 4px;
    transition: all 0.2s ease;
  }
  .save-card:hover {
    border-color: rgba(0, 255, 153, 0.3);
    background: rgba(0, 255, 153, 0.08);
  }
  .save-card.confirm-delete {
    border-color: rgba(255, 68, 68, 0.5);
    background: rgba(255, 68, 68, 0.1);
  }
  .save-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .save-name {
    font-size: 16px;
    font-weight: 600;
    color: #00ff99;
    font-family: 'JetBrains Mono', monospace;
  }
  .save-date {
    font-size: 12px;
    color: rgba(180, 200, 180, 0.5);
    font-family: 'JetBrains Mono', monospace;
  }
  .save-actions {
    display: flex;
    gap: 8px;
  }
  .action-btn {
    padding: 8px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid rgba(0, 255, 153, 0.2);
    border-radius: 2px;
    cursor: pointer;
    transition: all 0.15s ease;
    background: #1a1a1a;
    color: rgba(180, 200, 180, 0.9);
  }
  .action-btn:hover:not(:disabled) {
    border-color: #00ff99;
    color: #00ff99;
    background: rgba(0, 255, 153, 0.05);
  }
  .action-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .load-btn {
    min-width: 80px;
  }
  .delete-btn {
    width: 40px;
    padding: 8px 0;
  }
  .delete-btn.confirming {
    border-color: rgba(255, 68, 68, 0.5);
    color: #ff4444;
    background: rgba(255, 68, 68, 0.1);
  }
  .button-group {
    display: flex;
    gap: 16px;
    margin-top: 16px;
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
