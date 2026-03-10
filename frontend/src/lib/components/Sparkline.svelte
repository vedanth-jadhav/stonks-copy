<script lang="ts">
  export let values: number[] = [];
  export let tone: 'emerald' | 'amber' | 'crimson' | 'cobalt' = 'emerald';

  $: points = (() => {
    if (!values.length) return "";
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = Math.max(max - min, 0.0001);

    // Scale to a 100x40 viewBox for better aspect ratio in sparklines
    return values
      .map((value, index) => {
        const x = values.length === 1 ? 0 : (index / (values.length - 1)) * 100;
        const y = 40 - ((value - min) / span) * 40;
        return `${x},${y}`;
      })
      .join(" ");
  })();

  $: fillPoints = points ? `0,40 ${points} 100,40` : "";
</script>

<div class="sparkline-wrapper">
  <svg class="sparkline" viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
    <defs>
      <linearGradient id="spark-grad-{tone}" x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stop-color="var(--{tone})" stop-opacity="0.2" />
        <stop offset="100%" stop-color="var(--{tone})" stop-opacity="0" />
      </linearGradient>
    </defs>

    {#if fillPoints}
      <polyline points={fillPoints} fill="url(#spark-grad-{tone})" stroke="none" />
    {/if}

    <polyline
      points={points}
      fill="none"
      stroke="var(--{tone})"
      stroke-width="1.5"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="spark-path"
    />
  </svg>
</div>

<style>
  .sparkline-wrapper {
    width: 100%;
    height: 100%;
    overflow: visible;
  }

  .sparkline {
    width: 100%;
    height: 100%;
    display: block;
  }

  .spark-path {
    filter: drop-shadow(0 0 2px var(--emerald-glow));
  }
</style>
