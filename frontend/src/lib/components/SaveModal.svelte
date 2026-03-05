<script lang="ts">
  import { currentLang } from '$lib/stores/i18n.js';
  import { t } from '$lib/stores/i18n.js';
  import { saveGame, overwriteSave, type SaveMetadata } from '$lib/tauri/api';
  import { toast } from '$lib/stores/toast';
  import MechButton from './MechButton.svelte';
  import LoadingSpinner from './LoadingSpinner.svelte';
  
  let { existingSaves = [], currentSaveId = null, onClose }: { existingSaves?: SaveMetadata[], currentSaveId?: number | null, onClose: () => void } = $props();
  
  let saveName = '';
  let isSaving = false;
  let selectedSaveId: number | null = null;
  let lang = $currentLang;
  
  const placeholderText = lang === 'zh' ? '输入存档名称...' : 'Enter save name...';
  const saveButtonText = lang === 'zh' ? '保存' : 'SAVE';
  const overwriteButtonText = lang === 'zh' ? '覆盖选中存档' : 'OVERWRITE SELECTED';
  const cancelButtonText = lang === 'zh' ? '取消' : 'CANCEL';
  const titleText = lang === 'zh' ? '保存游戏' : 'Save Game';
  const overwriteHint = lang === 'zh' 
    ? '选择一个存档进行覆盖，或输入新名称创建新存档' 
    : 'Select a save to overwrite, or enter a new name to create a new save.';
  
  async function handleSave() {
    if (!saveName.trim()) {
      toast.error(lang === 'zh' ? '请输入存档名称' : 'Please enter a save name', 3000);
      return;
    }
    
    isSaving = true;
    try {
      if (selectedSaveId !== null) {
        await overwriteSave(saveName.trim(), selectedSaveId);
        toast.success(lang === 'zh' ? '存档已覆盖' : 'Save overwritten', 3000);
      } else {
        const newId = await saveGame(saveName.trim());
        toast.success(lang === 'zh' ? '游戏已保存' : 'Game saved', 3000);
      }
      onClose();
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      toast.error((lang === 'zh' ? '保存失败：' : 'Failed to save: ') + errorMsg, 5000);
      console.error('Failed to save game:', e);
    } finally {
      isSaving = false;
    }
  }
  
  function selectSave(save: SaveMetadata) {
    selectedSaveId = selectedSaveId === save.id ? null : save.id;
    if (selectedSaveId === save.id && !saveName) {
      saveName = save.name;
    }
  }
  
  function handleBack() {
    onClose();
  }
</script>

<div class="save-modal-overlay" on:click|self={handleBack}>
  <div class="save-modal">
    <h2 class="modal-title">{titleText}</h2>
    
    <div class="save-input-group">
      <input
        type="text"
        class="save-input"
        bind:value={saveName}
        placeholder={placeholderText}
        maxlength={100}
        disabled={isSaving}
      />
    </div>
    
    <p class="hint-text">{overwriteHint}</p>
    
    {#if existingSaves.length > 0}
      <div class="saves-list">
        {#each existingSaves as save (save.id)}
          <button
            class="save-item {selectedSaveId === save.id ? 'selected' : ''} {currentSaveId === save.id ? 'current' : ''}"
            on:click={() => selectSave(save)}
            disabled={isSaving}
          >
            <div class="save-item-info">
              <div class="save-item-name">{save.name}</div>
              <div class="save-item-date">
                {new Date(save.updated_at).toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US')}
              </div>
              {#if currentSaveId === save.id}
                <span class="current-badge">{lang === 'zh' ? '当前存档' : 'Current'}</span>
              {/if}
            </div>
          </button>
        {/each}
      </div>
    {:else}
      <p class="no-saves">{lang === 'zh' ? '暂无存档' : 'No saves yet'}</p>
    {/if}
    
    <div class="button-group">
      <MechButton onclick={handleSave} disabled={isSaving || !saveName.trim()}>
        {isSaving ? '⏳' : (selectedSaveId !== null ? overwriteButtonText : saveButtonText)}
      </MechButton>
      <MechButton onclick={handleBack} disabled={isSaving}>
        {cancelButtonText}
      </MechButton>
    </div>
    
    {#if isSaving}
      <div class="saving-indicator">
        <LoadingSpinner size={20} />
        <span>{lang === 'zh' ? '保存中...' : 'Saving...'}</span>
      </div>
    {/if}
  </div>
</div>

<style>
  .save-modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }
  .save-modal {
    background: #0a0a0a;
    border: 1px solid rgba(0, 255, 153, 0.2);
    border-radius: 4px;
    padding: 32px;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
    box-shadow: 0 0 40px rgba(0, 255, 153, 0.1);
  }
  .modal-title {
    font-size: 24px;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #00ff99;
    margin-bottom: 24px;
    font-family: 'JetBrains Mono', monospace;
    text-align: center;
  }
  .save-input-group {
    margin-bottom: 16px;
  }
  .save-input {
    width: 100%;
    padding: 12px 16px;
    background: rgba(0, 255, 153, 0.05);
    border: 1px solid rgba(0, 255, 153, 0.2);
    border-radius: 2px;
    color: #00ff99;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    outline: none;
    transition: all 0.2s;
  }
  .save-input:focus {
    border-color: #00ff99;
    background: rgba(0, 255, 153, 0.08);
  }
  .save-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .hint-text {
    font-size: 12px;
    color: rgba(180, 200, 180, 0.5);
    margin-bottom: 16px;
    text-align: center;
  }
  .saves-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 24px;
    max-height: 200px;
    overflow-y: auto;
  }
  .save-item {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    background: rgba(0, 255, 153, 0.05);
    border: 1px solid rgba(0, 255, 153, 0.1);
    border-radius: 2px;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
    width: 100%;
  }
  .save-item:hover:not(:disabled) {
    border-color: rgba(0, 255, 153, 0.3);
    background: rgba(0, 255, 153, 0.08);
  }
  .save-item.selected {
    border-color: #00ff99;
    background: rgba(0, 255, 153, 0.1);
  }
  .save-item.current {
    border-color: rgba(255, 215, 0, 0.5);
  }
  .save-item:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .save-item-info {
    flex: 1;
  }
  .save-item-name {
    font-size: 14px;
    font-weight: 600;
    color: #00ff99;
    font-family: 'JetBrains Mono', monospace;
  }
  .save-item-date {
    font-size: 11px;
    color: rgba(180, 200, 180, 0.5);
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
  }
  .current-badge {
    display: inline-block;
    font-size: 10px;
    color: #ffd700;
    border: 1px solid rgba(255, 215, 0, 0.5);
    padding: 2px 6px;
    border-radius: 2px;
    margin-top: 4px;
    font-family: 'JetBrains Mono', monospace;
  }
  .no-saves {
    text-align: center;
    color: rgba(180, 200, 180, 0.5);
    margin-bottom: 24px;
    font-size: 14px;
  }
  .button-group {
    display: flex;
    gap: 16px;
    justify-content: center;
  }
  .saving-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: rgba(180, 200, 180, 0.7);
    font-size: 13px;
    margin-top: 16px;
  }
</style>
