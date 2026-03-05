<script lang="ts">
  import { onMount, tick } from 'svelte';

  export let text: string = '';
  export let speed: number = 30; // 打字速度（毫秒/字符）
  export let className: string = '';
  export let showCursor: boolean = true;
  export let onComplete: (() => void) | null = null;

  let displayText = '';
  let isTyping = false;
  let currentIndex = 0;
  let typingTimeout: ReturnType<typeof setTimeout> | null = null;

  // 支持 HTML 标签
  const TAG_REGEX = /<[^>]+>/g;

  function getVisibleLength(str: string): number {
    return str.replace(TAG_REGEX, '').length;
  }

  function typeNextChar() {
    if (currentIndex >= text.length) {
      isTyping = false;
      if (onComplete) onComplete();
      return;
    }

    const nextChar = text[currentIndex];
    displayText += nextChar;
    currentIndex++;

    // 如果是 HTML 标签，立即显示整个标签
    if (nextChar === '<') {
      const tagEnd = text.indexOf('>', currentIndex);
      if (tagEnd !== -1) {
        displayText += text.slice(currentIndex, tagEnd + 1);
        currentIndex = tagEnd + 1;
      }
    }

    typingTimeout = setTimeout(typeNextChar, speed);
  }

  export function startTyping(newText: string = text) {
    if (typingTimeout) clearTimeout(typingTimeout);
    displayText = '';
    currentIndex = 0;
    isTyping = true;
    text = newText;
    typeNextChar();
  }

  export function skipToEnd() {
    if (typingTimeout) clearTimeout(typingTimeout);
    displayText = text;
    currentIndex = text.length;
    isTyping = false;
    if (onComplete) onComplete();
  }

  export function reset() {
    if (typingTimeout) clearTimeout(typingTimeout);
    displayText = '';
    currentIndex = 0;
    isTyping = false;
  }

  onMount(() => {
    if (text) {
      startTyping(text);
    }
    return () => {
      if (typingTimeout) clearTimeout(typingTimeout);
    };
  });

  // 当 text 属性变化时重新打字
  $: if (text && !isTyping && displayText !== text) {
    startTyping(text);
  }
</script>

<span class="typewriter-text {className}" class:typing={isTyping}>
  {@html displayText}{#if showCursor && isTyping}<span class="typewriter-cursor"></span>{/if}
</span>
