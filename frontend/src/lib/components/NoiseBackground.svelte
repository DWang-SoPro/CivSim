<script lang="ts">
  export let opacity = 0.03;
  export let blendMode: 'overlay' | 'multiply' | 'normal' = 'overlay';
</script>

<div class="noise-overlay" style="--noise-opacity: {opacity}; --blend-mode: {blendMode}">
  <svg class="noise-svg" xmlns="http://www.w3.org/2000/svg">
    <filter id="noiseFilter">
      <feTurbulence 
        type="fractalNoise" 
        baseFrequency="0.8" 
        numOctaves="4" 
        stitchTiles="stitch"
      />
      <feColorMatrix type="saturate" values="0"/>
    </filter>
    <rect width="100%" height="100%" filter="url(#noiseFilter)"/>
  </svg>
</div>

<style>
  .noise-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9999;
    opacity: var(--noise-opacity);
    mix-blend-mode: var(--blend-mode);
  }

  .noise-svg {
    width: 100%;
    height: 100%;
  }
</style>
