<script lang="ts">
  // LED 状态类型
  export let status: 'idle' | 'active' | 'success' | 'warning' | 'error' | 'processing' = 'idle';
  export let size: 'sm' | 'md' | 'lg' = 'md';
  export let label = '';
  export let pulse = true; // 是否启用脉冲动画
  
  // 状态颜色配置
  const statusColors = {
    idle: { bg: '#1a2a1a', glow: 'rgba(42, 58, 42, 0.5)', blink: false },
    active: { bg: '#c9a227', glow: 'rgba(201, 162, 39, 0.6)', blink: true },
    success: { bg: '#5a8a4a', glow: 'rgba(90, 138, 74, 0.6)', blink: false },
    warning: { bg: '#b87333', glow: 'rgba(184, 115, 51, 0.6)', blink: true },
    error: { bg: '#8b4513', glow: 'rgba(139, 69, 19, 0.8)', blink: true },
    processing: { bg: '#4a90d9', glow: 'rgba(74, 144, 217, 0.6)', blink: true }
  };
  
  // 尺寸配置
  const sizeConfig = {
    sm: { led: 6, font: '10px' },
    md: { led: 10, font: '12px' },
    lg: { led: 14, font: '14px' }
  };
  
  $: currentColor = statusColors[status];
  $: currentSize = sizeConfig[size];
</script>

<div class="status-led-container" style="font-size: {currentSize.font}">
  <!-- LED 灯 -->
  <div 
    class="led"
    class:pulsing={pulse && currentColor.blink}
    style="
      width: {currentSize.led}px; 
      height: {currentSize.led}px;
      background: {currentColor.bg};
      box-shadow: 
        0 0 {currentSize.led * 0.8}px {currentColor.glow},
        0 0 {currentSize.led * 1.5}px {currentColor.glow},
        inset 0 1px 2px rgba(255,255,255,0.3),
        inset 0 -1px 2px rgba(0,0,0,0.3);
    "
  >
    <!-- 高光反射 -->
    <div class="led-highlight"></div>
  </div>
  
  <!-- 标签 -->
  {#if label}
    <span class="led-label">{label}</span>
  {/if}
</div>

<style>
  .status-led-container {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-family: 'Courier Prime', monospace;
  }
  
  .led {
    position: relative;
    border-radius: 50%;
    transition: all 0.3s ease;
  }
  
  .led-highlight {
    position: absolute;
    top: 15%;
    left: 20%;
    width: 30%;
    height: 25%;
    background: radial-gradient(
      ellipse at center,
      rgba(255, 255, 255, 0.8) 0%,
      rgba(255, 255, 255, 0.2) 50%,
      transparent 70%
    );
    border-radius: 50%;
    pointer-events: none;
  }
  
  /* 脉冲动画 */
  .led.pulsing {
    animation: led-pulse 1.5s ease-in-out infinite;
  }
  
  @keyframes led-pulse {
    0%, 100% {
      opacity: 1;
      transform: scale(1);
    }
    50% {
      opacity: 0.6;
      transform: scale(0.95);
    }
  }
  
  /* 错误状态的快速闪烁 */
  .led.pulsing[style*="#8b4513"] {
    animation: led-blink 0.5s ease-in-out infinite;
  }
  
  @keyframes led-blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
  
  /* 处理中的呼吸效果 */
  .led.pulsing[style*="#4a90d9"] {
    animation: led-breathe 2s ease-in-out infinite;
  }
  
  @keyframes led-breathe {
    0%, 100% {
      box-shadow: 
        0 0 5px rgba(74, 144, 217, 0.4),
        0 0 10px rgba(74, 144, 217, 0.3),
        inset 0 1px 2px rgba(255,255,255,0.3);
    }
    50% {
      box-shadow: 
        0 0 15px rgba(74, 144, 217, 0.8),
        0 0 30px rgba(74, 144, 217, 0.5),
        inset 0 1px 2px rgba(255,255,255,0.3);
    }
  }
  
  .led-label {
    color: #b8b098;
    font-size: inherit;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
</style>
