<script lang="ts">
  import { onMount } from "svelte";
  import { goto } from "$app/navigation";
  import { formatDateTime, formatTime } from "$lib/format";
  import type { SystemMapPayload, SystemNode } from "$lib/api";

  export let map: SystemMapPayload;
  export let selectedNodeId = "";
  export let onSelect: (nodeId: string) => void;

  let container: HTMLElement;
  let lines: { x1: number; y1: number; x2: number; y2: number; active: boolean }[] = [];

  function updateLines() {
    if (!container) return;
    const newLines = [];
    const stageElements = container.querySelectorAll('.flow-stage');

    for (let i = 0; i < stageElements.length - 1; i++) {
      const currentStage = stageElements[i];
      const nextStage = stageElements[i + 1];

      const currentRect = currentStage.getBoundingClientRect();
      const nextRect = nextStage.getBoundingClientRect();
      const containerRect = container.getBoundingClientRect();

      const x1 = currentRect.right - containerRect.left;
      const y1 = currentRect.top + currentRect.height / 2 - containerRect.top;
      const x2 = nextRect.left - containerRect.left;
      const y2 = nextRect.top + nextRect.height / 2 - containerRect.top;

      newLines.push({ x1, y1, x2, y2, active: true });
    }
    lines = newLines;
  }

  onMount(() => {
    updateLines();
    window.addEventListener('resize', updateLines);
    return () => window.removeEventListener('resize', updateLines);
  });

  $: if (map) setTimeout(updateLines, 0);

  function primaryMetric(node: SystemNode) {
    return node.metric ? `${node.metric.label}: ${node.metric.value}` : "NO DATA";
  }
</script>

<div class="system-board-container" bind:this={container}>
  <svg class="flow-lines">
    <defs>
      <linearGradient id="line-grad" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="var(--emerald)" stop-opacity="0.2" />
        <stop offset="50%" stop-color="var(--emerald)" stop-opacity="0.6" />
        <stop offset="100%" stop-color="var(--emerald)" stop-opacity="0.2" />
      </linearGradient>
    </defs>
    {#each lines as line}
      <path
        d="M {line.x1} {line.y1} C {(line.x1 + line.x2) / 2} {line.y1}, {(line.x1 + line.x2) / 2} {line.y2}, {line.x2} {line.y2}"
        stroke="url(#line-grad)"
        stroke-width="2"
        fill="none"
        class="pulse-path"
      />
      <circle r="3" fill="var(--emerald)" class="data-particle">
        <animateMotion
          dur="3s"
          repeatCount="indefinite"
          path="M {line.x1} {line.y1} C {(line.x1 + line.x2) / 2} {line.y1}, {(line.x1 + line.x2) / 2} {line.y2}, {line.x2} {line.y2}"
        />
      </circle>
    {/each}
  </svg>

  <div class="system-board-track">
    {#each map.stages as stage}
      {@const nodes = map.nodes.filter(n => n.stage === stage.id)}
      <section class="flow-stage">
        <div class="stage-header">
          <span class="mono text-emerald opacity-50 text-[10px] tracking-tighter">{stage.id.toUpperCase()}</span>
          <h3 class="text-xs font-bold tracking-widest uppercase opacity-80">{stage.caption}</h3>
        </div>

        <div class="node-stack">
          {#each nodes as node}
            <button
              class="node-card"
              class:selected={selectedNodeId === node.id}
              class:border-emerald={node.status === 'healthy'}
              class:border-amber={node.status === 'warning'}
              class:border-crimson={node.status === 'critical'}
              on:click={() => onSelect(node.id)}
            >
              <div class="flex justify-between items-start mb-2">
                <span class="text-[10px] font-bold uppercase tracking-tighter opacity-60">{node.label}</span>
                <div class="w-1.5 h-1.5 rounded-full" class:bg-emerald={node.status === 'healthy'} class:bg-amber={node.status === 'warning'} class:bg-crimson={node.status === 'critical'}></div>
              </div>

              <div class="mono text-xs font-medium mb-1 truncate">{primaryMetric(node)}</div>
              <div class="text-[9px] opacity-40 uppercase">{formatTime(node.updated_at)}</div>
            </button>
          {/each}
        </div>
      </section>
    {/each}

    <section class="flow-stage boss-stage">
      <div class="stage-header">
        <span class="mono text-amber opacity-50 text-[10px] tracking-tighter">TERMINAL</span>
        <h3 class="text-xs font-bold tracking-widest uppercase opacity-80">BOSS CORE</h3>
      </div>

      <div class="boss-radar-container">
        <button
          class="boss-radar"
          class:selected={selectedNodeId === 'boss'}
          on:click={() => onSelect('boss')}
        >
          <div class="radar-rings">
            <div class="ring"></div>
            <div class="ring"></div>
            <div class="ring"></div>
          </div>
          <div class="radar-content">
            <div class="text-[10px] opacity-60 uppercase mb-1">Decision</div>
            <div class="mono text-xl font-bold text-amber">{map.boss.value}</div>
          </div>
        </button>

        <button class="mt-4 text-[10px] font-bold uppercase tracking-widest text-amber hover:underline" on:click={() => goto(map.boss.route)}>
          Review Protocol →
        </button>
      </div>
    </section>
  </div>
</div>

<style>
  .system-board-container {
    position: relative;
    width: 100%;
    min-height: 600px;
    padding: 40px 0;
    overflow-x: auto;
    overflow-y: hidden;
  }

  .flow-lines {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 1;
  }

  .system-board-track {
    display: flex;
    gap: 80px;
    padding: 0 40px;
    position: relative;
    z-index: 2;
    min-width: max-content;
  }

  .flow-stage {
    width: 180px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .stage-header {
    display: flex;
    flex-direction: column;
    gap: 4px;
    border-left: 2px solid var(--obsidian-600);
    padding-left: 12px;
  }

  .node-stack {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .node-card {
    background: var(--obsidian-800);
    border: 1px solid var(--border-subtle);
    padding: 12px;
    text-align: left;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
  }

  .node-card:hover {
    background: var(--obsidian-700);
    transform: translateX(4px);
    border-color: var(--emerald);
  }

  .node-card.selected {
    background: var(--emerald-dim);
    border-color: var(--emerald);
    box-shadow: 0 0 20px var(--emerald-glow);
  }

  .boss-radar-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 20px;
  }

  .boss-radar {
    width: 140px;
    height: 140px;
    border-radius: 50%;
    background: var(--obsidian-800);
    border: 1px solid var(--amber);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    transition: all 0.3s ease;
    cursor: pointer;
  }

  .boss-radar.selected {
    box-shadow: 0 0 30px var(--amber-glow);
    background: var(--amber-dim);
  }

  .radar-rings .ring {
    position: absolute;
    inset: 0;
    border: 1px solid var(--amber);
    border-radius: 50%;
    opacity: 0.1;
    animation: radar-ping 4s infinite cubic-bezier(0, 0, 0.2, 1);
  }

  .radar-rings .ring:nth-child(2) { animation-delay: 1.3s; }
  .radar-rings .ring:nth-child(3) { animation-delay: 2.6s; }

  @keyframes radar-ping {
    0% { transform: scale(1); opacity: 0.3; }
    100% { transform: scale(1.5); opacity: 0; }
  }

  .radar-content {
    text-align: center;
    z-index: 2;
  }

  .pulse-path {
    stroke-dasharray: 4, 4;
    animation: dash-move 20s linear infinite;
  }

  @keyframes dash-move {
    from { stroke-dashoffset: 200; }
    to { stroke-dashoffset: 0; }
  }

  .data-particle {
    filter: drop-shadow(0 0 4px var(--emerald));
  }

  .bg-emerald { background-color: var(--emerald); }
  .bg-amber { background-color: var(--amber); }
  .bg-crimson { background-color: var(--crimson); }
  .text-emerald { color: var(--emerald); }
  .text-amber { color: var(--amber); }
  .border-emerald { border-color: var(--emerald); }
  .border-amber { border-color: var(--amber); }
  .border-crimson { border-color: var(--crimson); }
</style>
