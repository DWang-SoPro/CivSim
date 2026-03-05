<script lang="ts">
  export let size = 24;
  export let color = '#00ff99';
</script>

<div class="spinner" style="width: {size}px; height: {size}px;">
  <svg viewBox="0 0 24 24" style="stroke: {color};">
    <circle
      class="spinner-circle"
      cx="12"
      cy="12"
      r="10"
      fill="none"
      stroke-width="2"
    />
  </svg>
</div>

<style>
  .spinner {
    display: inline-block;
    animation: spin 1s linear infinite;
  }
  
  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  
  .spinner-circle {
    stroke-dasharray: 60;
    stroke-dashoffset: 45;
    animation: dash 1.5s ease-in-out infinite;
  }
  
  @keyframes dash {
    0% { stroke-dashoffset: 45; }
    50% { stroke-dashoffset: 15; }
    100% { stroke-dashoffset: 45; }
  }
</style>
