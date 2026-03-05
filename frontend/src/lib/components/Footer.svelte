<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { log } from '$lib/stores/gameLog.js';
  import { currentLang } from '$lib/stores/i18n.js';
  import { toast } from '$lib/stores/toast';
  import { processPlayerInput } from '$lib/tauri/api';
  import { civState, updateCivState } from '$lib/stores/civState.js';
  import LoadingSpinner from './LoadingSpinner.svelte';
  
  const dispatch = createEventDispatcher();
  
  let input = '';
  let isSubmitting = false;
  let lang = $currentLang;
  
  const t = (key: string) => {
    const translations: Record<string, Record<string, string>> = {
      zh: {
        'footer.placeholder': '请输入您的文明敕令...',
        'footer.submit': '执行',
        'footer.processing': 'AI 思考中...',
        'footer.enter_hint': '按 Enter 提交',
        'footer.natural_hint': '支持自然语言',
        'footer.error': '处理失败：',
        'footer.success': '指令已执行',
      },
      en: {
        'footer.placeholder': 'Enter your civilization decree...',
        'footer.submit': 'EXECUTE',
        'footer.processing': 'AI thinking...',
        'footer.enter_hint': 'PRESS ENTER TO SUBMIT',
        'footer.natural_hint': 'NATURAL LANGUAGE SUPPORTED',
        'footer.error': 'Error: ',
        'footer.success': 'Command executed',
      }
    };
    return translations[lang][key] || key;
  };
  
  async function handleSubmit() {
    if (!input.trim() || isSubmitting) return;
    
    isSubmitting = true;
    const command = input.trim();
    
    try {
      log(`**COMMAND**: ${command}`);
      
      // 调用后端 API
      const result = await processPlayerInput(command);
      
      // 显示成功提示
      toast.success(t('footer.success'));
      
      // 记录结果
      log(`**RESULT**: ${result.summary}`);
      
      // 更新状态 - 使用 updateCivState 确保响应式更新
      updateCivState(result.new_state);
      
      // 添加到日志（Markdown 格式）
      log(`\n${result.narrative}`);
      
      dispatch('submit', { text: command, result });
      
      input = '';
    } catch (error) {
      console.error('Failed to process command:', error);
      const errorMsg = error instanceof Error ? error.message : String(error);
      log(`${t('footer.error')}${errorMsg}`);
      toast.error(`${t('footer.error')}${errorMsg}`, 5000);
    } finally {
      isSubmitting = false;
    }
  }
  
  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  }
</script>

<footer class="footer">
  <div class="footer-content">
    <div class="input-wrapper">
      <span class="input-prompt">></span>
      <input
        type="text"
        class="command-input"
        bind:value={input}
        on:keydown={handleKeydown}
        placeholder={t('footer.placeholder')}
        disabled={isSubmitting}
      />
    </div>
    
    <button 
      class="submit-btn"
      on:click={handleSubmit}
      disabled={isSubmitting || !input.trim()}
    >
      {#if isSubmitting}
        <LoadingSpinner size={16} />
        <span style="margin-left: 8px;">{t('footer.processing')}</span>
      {:else}
        {t('footer.submit')}
      {/if}
    </button>
  </div>
  
  <div class="footer-hint">
    <span>{t('footer.enter_hint')}</span>
    <span class="hint-divider">|</span>
    <span>{t('footer.natural_hint')}</span>
  </div>
</footer>

<style>
  .footer {
    height: auto;
    background: #0f0f0f;
    border-top: 1px solid rgba(0, 255, 153, 0.15);
    padding: 16px 24px;
    flex-shrink: 0;
  }
  .footer-content {
    display: flex;
    gap: 16px;
    align-items: center;
  }
  .input-wrapper {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 12px;
    background: #121212;
    border: 1px solid rgba(0, 255, 153, 0.15);
    padding: 0 16px;
  }
  .input-prompt {
    font-size: 16px;
    color: #00ff99;
    font-weight: 700;
  }
  .command-input {
    flex: 1;
    background: transparent;
    border: none;
    color: #00ff99;
    font-family: 'JetBrains Mono', monospace;
    font-size: 14px;
    padding: 14px 0;
  }
  .command-input:focus { outline: none; }
  .command-input::placeholder {
    color: rgba(180, 200, 180, 0.3);
  }
  .submit-btn {
    background: #1a1a1a;
    border: 1px solid rgba(0, 255, 153, 0.15);
    color: rgba(180, 200, 180, 0.9);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 14px 32px;
    cursor: pointer;
    transition: all 0.15s ease;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .submit-btn:hover:not(:disabled) {
    border-color: #00ff99;
    color: #00ff99;
    background: rgba(0, 255, 153, 0.05);
  }
  .submit-btn:active:not(:disabled) {
    transform: translateY(1px);
  }
  .submit-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
  .footer-hint {
    display: flex;
    gap: 12px;
    margin-top: 12px;
    font-size: 11px;
    color: rgba(180, 200, 180, 0.4);
    letter-spacing: 0.05em;
  }
  .hint-divider { opacity: 0.5; }
</style>
