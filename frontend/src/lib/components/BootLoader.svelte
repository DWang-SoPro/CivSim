<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { fly } from 'svelte/transition';

  const dispatch = createEventDispatcher();

  let progress = 0;
  let currentTask = 'INITIALIZING SYSTEM...';
  let showCursor = true;

  const tasks = [
    { message: 'INITIALIZING KERNEL...', delay: 200 },
    { message: 'LOADING MEMORY MODULES...', delay: 400 },
    { message: 'MOUNTING FILE SYSTEMS...', delay: 600 },
    { message: 'INITIALIZING AGENT PIPELINE...', delay: 800 },
    { message: 'CONNECTING TO DASHSCOPE API...', delay: 1000 },
    { message: 'CALIBRATING MATHEMATICAL MODELS...', delay: 1200 },
    { message: 'LOADING CIVILIZATION DATABASE...', delay: 1400 },
    { message: 'SYSTEM READY', delay: 1600 },
  ];

  // Cursor blink
  const cursorInterval = setInterval(() => {
    showCursor = !showCursor;
  }, 500);

  // Progress simulation
  let taskIndex = 0;
  const progressInterval = setInterval(() => {
    if (progress < 100) {
      progress += Math.random() * 15;
      if (progress > 100) progress = 100;

      // Update task message
      const newTaskIndex = Math.floor((progress / 100) * tasks.length);
      if (newTaskIndex > taskIndex && newTaskIndex < tasks.length) {
        taskIndex = newTaskIndex;
        currentTask = tasks[taskIndex].message;
      }
    } else {
      clearInterval(progressInterval);
      clearInterval(cursorInterval);
      setTimeout(() => {
        dispatch('complete');
      }, 500);
    }
  }, 150);

  function formatProgress(p: number): string {
    return Math.min(100, Math.floor(p)).toString().padStart(3, '0');
  }
</script>

<div
  class="fixed inset-0 z-50 bg-retro-bg flex flex-col items-center justify-center font-retro"
  transition:fly={{ duration: 300 }}
>
  <!-- Terminal Window -->
  <div class="w-[600px] retro-panel">
    <!-- Title Bar -->
    <div class="retro-title-bar px-3 py-2 flex items-center justify-between">
      <span class="text-xs text-retro-dim">SYSTEM BOOT</span>
      <div class="flex gap-1">
        <div class="w-2 h-2 bg-retro-border"></div>
        <div class="w-2 h-2 bg-retro-border"></div>
      </div>
    </div>

    <!-- Content -->
    <div class="p-6 space-y-4">
      <!-- Logo/Header -->
      <div class="text-center mb-6">
        <div class="text-retro-accent font-display text-3xl mb-2 tracking-widest">
          文明灵
        </div>
        <div class="text-retro-dim text-xs tracking-[0.5em]">
          CIVILIZATION SIMULATOR v0.1.0
        </div>
      </div>

      <!-- Boot Messages -->
      <div class="font-display text-lg text-retro-success space-y-1">
        {#each tasks.slice(0, taskIndex + 1) as task, i}
          <div class="flex items-center gap-2">
            <span class="text-retro-accent">[</span>
            <span>{task.message}</span>
            <span class="text-retro-accent">]</span>
            {#if i === taskIndex && progress < 100}
              <span class="text-retro-accent" class:opacity-0={!showCursor}>_</span>
            {:else}
              <span class="text-retro-success">OK</span>
            {/if}
          </div>
        {/each}
      </div>

      <!-- Progress Bar -->
      <div class="mt-6">
        <div class="flex justify-between text-xs text-retro-dim mb-2">
          <span>PROGRESS</span>
          <span>{formatProgress(progress)}%</span>
        </div>
        <div class="retro-progress-bar">
          <div
            class="retro-progress-fill"
            style="width: {Math.min(100, progress)}%"
          ></div>
        </div>
      </div>

      <!-- Bottom Decoration -->
      <div class="flex justify-center gap-4 mt-6">
        {#each Array(5) as _, i}
          <div
            class="w-2 h-2 border border-retro-border"
            class:bg-retro-accent={progress > (i + 1) * 20}
            class:bg-transparent={progress <= (i + 1) * 20}
          ></div>
        {/each}
      </div>
    </div>

    <!-- Corner Decorations -->
    <div class="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-retro-accent"></div>
    <div class="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-retro-accent"></div>
    <div class="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-retro-accent"></div>
    <div class="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-retro-accent"></div>
  </div>

  <!-- Bottom Status -->
  <div class="mt-8 text-xs text-retro-dim font-display tracking-wider">
    PRESS ANY KEY TO SKIP_{showCursor ? '█' : ' '}
  </div>
</div>

<style>
  .retro-panel {
    position: relative;
    background: #0a0f0a;
    border: 1px solid #1a2a1a;
    box-shadow:
      0 0 20px rgba(201, 162, 39, 0.1),
      inset 0 1px 0 rgba(184, 176, 152, 0.05);
  }

  .retro-title-bar {
    background: #141f14;
    border-bottom: 1px solid #1a2a1a;
  }

  .retro-progress-bar {
    height: 8px;
    background: #0a0f0a;
    border: 1px solid #1a2a1a;
    position: relative;
  }

  .retro-progress-bar::before {
    content: '';
    position: absolute;
    inset: 1px;
    background: repeating-linear-gradient(
      90deg,
      transparent,
      transparent 8px,
      #1a2a1a 8px,
      #1a2a1a 9px
    );
  }

  .retro-progress-fill {
    height: 100%;
    background: linear-gradient(
      90deg,
      #5a8a4a 0%,
      #c9a227 50%,
      #5a8a4a 100%
    );
    position: relative;
    z-index: 1;
    transition: width 0.1s linear;
  }

  .retro-progress-fill::after {
    content: '';
    position: absolute;
    right: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: #b8b098;
    box-shadow: 0 0 8px #c9a227;
  }
</style>
