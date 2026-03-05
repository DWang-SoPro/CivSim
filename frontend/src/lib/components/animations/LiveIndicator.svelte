<script lang="ts">
  export let status: 'online' | 'offline' | 'processing' | 'error' = 'online';
  export let size: 'sm' | 'md' | 'lg' = 'sm';
  export let showLabel: boolean = true;
  export let label: string = '';
  export let pulseSpeed: 'slow' | 'normal' | 'fast' = 'normal';

  const sizeClasses = {
    sm: 'w-2 h-2',
    md: 'w-3 h-3',
    lg: 'w-4 h-4'
  };

  const statusColors = {
    online: 'bg-retro-success',
    offline: 'bg-retro-dim',
    processing: 'bg-retro-accent',
    error: 'bg-retro-danger'
  };

  const statusLabels: Record<string, string> = {
    online: '在线',
    offline: '离线',
    processing: '处理中',
    error: '错误'
  };

  const pulseSpeeds = {
    slow: 'signal-pulse-slow',
    normal: 'signal-pulse',
    fast: 'signal-pulse-fast'
  };

  $: displayLabel = label || statusLabels[status];
  $: shouldPulse = status === 'processing' || status === 'online';
</script>

<div class="flex items-center gap-2" title={displayLabel}>
  <span 
    class="signal-dot {sizeClasses[size]} rounded-full {statusColors[status]}"
    class:signal-pulse={shouldPulse && pulseSpeed === 'normal'}
    class:signal-pulse-slow={shouldPulse && pulseSpeed === 'slow'}
    class:signal-pulse-fast={shouldPulse && pulseSpeed === 'fast'}
  ></span>
  {#if showLabel}
    <span class="text-xs text-retro-dim">{displayLabel}</span>
  {/if}
</div>
