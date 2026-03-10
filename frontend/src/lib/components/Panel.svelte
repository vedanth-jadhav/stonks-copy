<script lang="ts">
  export let eyebrow = "";
  export let title = "";
  export let compact = false;
  export let tone = ""; // "emerald", "amber", "crimson"
</script>

<section
  class="panel"
  class:panel--compact={compact}
  class:border-emerald={tone === 'emerald'}
  class:border-amber={tone === 'amber'}
  class:border-crimson={tone === 'crimson'}
>
  {#if eyebrow || title}
    <header class="panel__head">
      <div class="status-metric">
        {#if eyebrow}<span class="status-metric__label">{eyebrow}</span>{/if}
        {#if title}<h2 class="status-metric__value">{title}</h2>{/if}
      </div>
      <slot name="head" />
    </header>
  {/if}

  <div class="panel__content">
    <slot />
  </div>

  <!-- Tactical HUD Details -->
  <div class="hud-decor-tl"></div>
  <div class="hud-decor-br"></div>
</section>

<style>
  .panel {
    background: var(--obsidian-800);
    border: 1px solid var(--border-subtle);
    padding: 20px;
    position: relative;
    overflow: hidden;
    transition: all 0.2s ease;
  }

  .panel--compact {
    padding: 12px;
  }

  .panel__head {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--obsidian-700);
  }

  .panel__content {
    position: relative;
    z-index: 2;
  }

  .hud-decor-tl, .hud-decor-br {
    position: absolute;
    width: 12px;
    height: 12px;
    pointer-events: none;
    z-index: 3;
    opacity: 0.6;
  }

  .hud-decor-tl {
    top: 0;
    left: 0;
    border-top: 2px solid var(--emerald);
    border-left: 2px solid var(--emerald);
  }

  .hud-decor-br {
    bottom: 0;
    right: 0;
    border-bottom: 2px solid var(--emerald);
    border-right: 2px solid var(--emerald);
  }

  .border-emerald .hud-decor-tl, .border-emerald .hud-decor-br { border-color: var(--emerald); }
  .border-amber .hud-decor-tl, .border-amber .hud-decor-br { border-color: var(--amber); }
  .border-crimson .hud-decor-tl, .border-crimson .hud-decor-br { border-color: var(--crimson); }

  .border-emerald { border-color: rgba(16, 185, 129, 0.2); }
  .border-amber { border-color: rgba(245, 158, 11, 0.2); }
  .border-crimson { border-color: rgba(239, 68, 68, 0.2); }
</style>
