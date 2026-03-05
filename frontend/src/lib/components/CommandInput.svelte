<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  
  export let value = '';
  export let placeholder = '';
  export let disabled = false;
  export let isFocused = false;
  
  let inputElement: HTMLInputElement;
  let isTyping = false;
  let typingTimeout: ReturnType<typeof setTimeout>;
  
  const dispatch = createEventDispatcher();
  
  export function focus() {
    inputElement?.focus();
  }
  
  function handleInput(event: Event) {
    const target = event.target as HTMLInputElement;
    value = target.value;
    dispatch('input', value);
    
    // 打字动画效果
    isTyping = true;
    clearTimeout(typingTimeout);
    typingTimeout = setTimeout(() => {
      isTyping = false;
    }, 150);
  }
  
  function handleKeydown(event: KeyboardEvent) {
    dispatch('keydown', event);
    
    if (event.key === 'Enter' && !event.shiftKey) {
      dispatch('submit', value);
    }
  }
  
  function handleFocus() {
    isFocused = true;
    dispatch('focus');
  }
  
  function handleBlur() {
    isFocused = false;
    dispatch('blur');
  }
</script>

<div class="command-input-wrapper" class:focused={isFocused} class:disabled class:typing={isTyping}>
  <!-- 扫描线背景 -->
  <div class="scanlines"></div>
  
  <!-- 辉光效果层 -->
  <div class="glow-layer"></div>
  
  <!-- 输入框 -->
  <input
    bind:this={inputElement}
    type="text"
    {value}
    {placeholder}
    {disabled}
    on:input={handleInput}
    on:keydown={handleKeydown}
    on:focus={handleFocus}
    on:blur={handleBlur}
    class="command-input"
  />
  
  <!-- 光标指示器 -->
  <div class="cursor-indicator" class:active={isFocused}></div>
</div>

<style>
  .command-input-wrapper {
    position: relative;
    width: 100%;
    height: 44px;
    background: #0a0f0a;
    border: 1px solid #2a3a2a;
    overflow: hidden;
    transition: all 0.2s ease;
  }
  
  .command-input-wrapper::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(42, 58, 42, 0.5), transparent);
    z-index: 3;
  }
  
  .command-input-wrapper.focused {
    border-color: #c9a227;
    box-shadow: 
      0 0 0 1px rgba(201, 162, 39, 0.2),
      0 0 20px rgba(201, 162, 39, 0.1),
      inset 0 0 20px rgba(201, 162, 39, 0.05);
  }
  
  .command-input-wrapper.disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  
  .command-input-wrapper.typing {
    border-color: rgba(201, 162, 39, 0.5);
  }
  
  /* 扫描线背景 */
  .scanlines {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    opacity: 0.03;
    background: repeating-linear-gradient(
      0deg,
      transparent,
      transparent 2px,
      rgba(201, 162, 39, 0.3) 2px,
      rgba(201, 162, 39, 0.3) 4px
    );
    z-index: 1;
  }
  
  /* 辉光层 */
  .glow-layer {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    opacity: 0;
    background: radial-gradient(
      ellipse at center bottom,
      rgba(201, 162, 39, 0.15) 0%,
      transparent 70%
    );
    transition: opacity 0.3s ease;
    z-index: 2;
  }
  
  .command-input-wrapper.focused .glow-layer {
    opacity: 1;
  }
  
  /* 输入框样式 */
  .command-input {
    position: relative;
    width: 100%;
    height: 100%;
    padding: 0 16px;
    padding-left: 20px;
    background: transparent;
    border: none;
    outline: none;
    color: #c9a227;
    font-family: 'Courier Prime', monospace;
    font-size: 14px;
    letter-spacing: 0.5px;
    z-index: 3;
  }
  
  .command-input::placeholder {
    color: #5a6050;
    font-style: italic;
  }
  
  .command-input:disabled {
    cursor: not-allowed;
  }
  
  /* 光标指示器 */
  .cursor-indicator {
    position: absolute;
    left: 8px;
    top: 50%;
    transform: translateY(-50%);
    width: 3px;
    height: 16px;
    background: #c9a227;
    opacity: 0;
    transition: opacity 0.2s ease;
    animation: cursor-blink 1s step-end infinite;
    z-index: 4;
  }
  
  .cursor-indicator.active {
    opacity: 0.6;
  }
  
  @keyframes cursor-blink {
    0%, 100% { opacity: 0.6; }
    50% { opacity: 0.1; }
  }
  
  /* 打字时的闪光效果 */
  .command-input-wrapper.typing::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: radial-gradient(
      ellipse at 20% 50%,
      rgba(201, 162, 39, 0.1) 0%,
      transparent 50%
    );
    pointer-events: none;
    z-index: 2;
    animation: typing-flash 0.15s ease-out;
  }
  
  @keyframes typing-flash {
    0% { opacity: 1; }
    100% { opacity: 0; }
  }
</style>
