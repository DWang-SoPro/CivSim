<script lang="ts">
  import { onMount, onDestroy } from 'svelte';

  export let value: number = 0;
  export let duration: number = 600; // 动画持续时间（毫秒）
  export let format: (n: number) => string = (n) => n.toLocaleString();
  export let className: string = '';
  export let direction: 'up' | 'down' | 'auto' = 'auto';

  let displayValue: number = value;
  let previousValue: number = value;
  let animationClass: string = '';
  let animationTimeout: ReturnType<typeof setTimeout> | null = null;
  let isAnimating = false;

  function easeOutCubic(t: number): number {
    return 1 - Math.pow(1 - t, 3);
  }

  function animateNumber(from: number, to: number) {
    if (isAnimating && animationTimeout) {
      clearTimeout(animationTimeout);
    }

    const startTime = Date.now();
    const diff = to - from;
    
    // 确定动画方向
    let animDir: 'up' | 'down';
    if (direction === 'auto') {
      animDir = diff > 0 ? 'up' : 'down';
    } else {
      animDir = direction;
    }

    // 设置动画类
    animationClass = `stat-change-${animDir}`;
    isAnimating = true;

    function step() {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);

      displayValue = from + diff * easedProgress;

      if (progress < 1) {
        animationTimeout = setTimeout(step, 16); // ~60fps
      } else {
        displayValue = to;
        isAnimating = false;
        // 清除动画类（延迟一点让用户看到效果）
        animationTimeout = setTimeout(() => {
          animationClass = '';
        }, 300);
      }
    }

    step();
  }

  $: {
    if (value !== previousValue) {
      animateNumber(previousValue, value);
      previousValue = value;
    }
  }

  onMount(() => {
    displayValue = value;
    previousValue = value;
  });

  onDestroy(() => {
    if (animationTimeout) clearTimeout(animationTimeout);
  });
</script>

<span class="{className} {animationClass}" class:animating={isAnimating}>
  {format(displayValue)}
</span>
