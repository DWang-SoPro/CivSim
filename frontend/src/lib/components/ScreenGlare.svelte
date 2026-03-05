<!-- 屏幕反光效果组件 - 模拟旧式CRT显示器的屏幕反光 -->
<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  
  let glareElement: HTMLDivElement;
  let animationFrameId: number;
  let isVisible = false;
  
  // 鼠标位置（归一化 0-1）
  let mouseX = 0.5;
  let mouseY = 0.5;
  
  // 平滑过渡的目标值
  let targetX = 0.5;
  let targetY = 0.5;
  
  // 平滑系数
  const smoothing = 0.08;
  
  function handleMouseMove(e: MouseEvent) {
    targetX = e.clientX / window.innerWidth;
    targetY = e.clientY / window.innerHeight;
  }
  
  function animate() {
    // 平滑插值
    mouseX += (targetX - mouseX) * smoothing;
    mouseY += (targetY - mouseY) * smoothing;
    
    if (glareElement) {
      // 计算反光位置 - 与鼠标相反方向移动
      const glareX = (1 - mouseX) * 100;
      const glareY = (1 - mouseY) * 100;
      
      glareElement.style.background = `
        radial-gradient(
          ellipse 80% 60% at ${glareX}% ${glareY}%,
          rgba(255, 255, 255, 0.03) 0%,
          rgba(255, 255, 255, 0.01) 30%,
          transparent 70%
        )
      `;
    }
    
    animationFrameId = requestAnimationFrame(animate);
  }
  
  onMount(() => {
    // 延迟显示，避免突兀
    setTimeout(() => {
      isVisible = true;
    }, 500);
    
    window.addEventListener('mousemove', handleMouseMove);
    animationFrameId = requestAnimationFrame(animate);
  });
  
  onDestroy(() => {
    window.removeEventListener('mousemove', handleMouseMove);
    if (animationFrameId) {
      cancelAnimationFrame(animationFrameId);
    }
  });
</script>

<div
  bind:this={glareElement}
  class="pointer-events-none fixed inset-0 z-[60] transition-opacity duration-1000"
  class:opacity-0={!isVisible}
  style="mix-blend-mode: overlay;"
/>

<!-- 静态环境反光层 -->
<div 
  class="pointer-events-none fixed inset-0 z-[59]"
  style="
    background: 
      linear-gradient(
        165deg,
        rgba(255, 255, 255, 0.02) 0%,
        transparent 40%,
        transparent 60%,
        rgba(255, 255, 255, 0.015) 100%
      );
    mix-blend-mode: soft-light;
  "
/>
