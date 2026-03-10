<script lang="ts">
  import { goto } from "$app/navigation";
  import { onMount } from "svelte";
  import Panel from "$components/Panel.svelte";
  import SystemBoard from "$components/SystemBoard.svelte";
  import { controlRoom } from "$lib/control-room";
  import { formatDateTime, formatTime } from "$lib/format";
  import { Activity, ShieldCheck, Zap, Layers, Clock } from "@lucide/svelte";

  let selectedNodeId = "agent_06_macro";

  onMount(() => {
    if (!$controlRoom.systemMap) {
      void controlRoom.refreshShell();
    }
    if (!$controlRoom.selectedAgent) {
      void controlRoom.selectAgent(selectedNodeId);
    }
  });

  $: if ($controlRoom.systemMap && !$controlRoom.systemMap.nodes.some((node) => node.id === selectedNodeId) && selectedNodeId !== "boss") {
    selectedNodeId = $controlRoom.systemMap.nodes[0]?.id ?? "boss";
  }

  $: selectedNode = selectedNodeId === "boss"
    ? null
    : $controlRoom.systemMap?.nodes.find((node) => node.id === selectedNodeId) ?? null;

  async function handleSelect(nodeId: string) {
    selectedNodeId = nodeId;
    if (nodeId !== "boss") {
      await controlRoom.selectAgent(nodeId);
    }
  }
</script>

{#if !$controlRoom.systemMap || !$controlRoom.overview}
  <div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Synchronizing Neural Links...</div>
  </div>
{:else}
  <div class="space-y-6">
    <section class="flex justify-between items-end border-b border-subtle pb-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 text-emerald">
          <ShieldCheck size={14} />
          <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Secure Command Environment</span>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">Tactical Operations <span class="text-emerald">HUD</span></h1>
        <p class="text-ink-secondary text-sm max-w-xl">Real-time pipeline monitoring and high-frequency signal arbitration.</p>
      </div>

      <div class="flex gap-4">
        <div class="status-metric text-right">
          <span class="status-metric__label">SIGNAL NODES</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.systemMap.memory_signal.nodes}</span>
        </div>
        <div class="status-metric text-right">
          <span class="status-metric__label">ACTIVE EDGES</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.systemMap.memory_signal.edges}</span>
        </div>
        <div class="status-metric text-right">
          <span class="status-metric__label">MARKET STATE</span>
          <span class="status-metric__value mono text-amber">{$controlRoom.overview.market.session_state}</span>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 xl-grid-cols-split gap-6 items-start">
      <Panel eyebrow="EXECUTION TOPOLOGY" title="Signal Flow Map" tone="emerald">
        <SystemBoard map={$controlRoom.systemMap} {selectedNodeId} onSelect={handleSelect} />
      </Panel>

      <Panel eyebrow="NODE DIAGNOSTICS" title={selectedNodeId === "boss" ? "TERMINAL CORE" : selectedNode?.label ?? "SELECTION"} tone={selectedNodeId === 'boss' ? 'amber' : 'emerald'}>
        {#if selectedNodeId === "boss"}
          <div class="space-y-6">
            <p class="text-xs text-ink-secondary leading-relaxed">Final portfolio arbitration and execution gate. All signals terminate here for final routing.</p>

            <div class="grid grid-cols-2 gap-4 border-y border-subtle py-4">
              <div class="status-metric">
                <span class="status-metric__label">STATUS</span>
                <span class="status-metric__value text-emerald">{$controlRoom.systemMap.boss.status}</span>
              </div>
              <div class="status-metric">
                <span class="status-metric__label">THROUGHPUT</span>
                <span class="status-metric__value mono">{$controlRoom.systemMap.boss.value}</span>
              </div>
            </div>

            <div class="space-y-3">
              <span class="status-metric__label">LATEST DECISIONS</span>
              <div class="space-y-2">
                {#each $controlRoom.overview.latest_decisions.slice(0, 4) as decision}
                  <div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-center group hover:border-emerald transition-colors">
                    <div class="flex flex-col">
                      <span class="mono text-xs font-bold text-emerald">{decision.ticker ?? "PORT"}</span>
                      <span class="text-[9px] text-ink-dim uppercase">Origin: {decision.origin ?? "SYS"}</span>
                    </div>
                    <div class="flex flex-col text-right">
                      <span class="mono text-xs font-bold" class:text-emerald={decision.decision === 'BUY'} class:text-crimson={decision.decision === 'SELL'}>{decision.decision ?? "HOLD"}</span>
                      <span class="text-[9px] text-ink-dim mono">C: {Number(decision.confidence ?? 0).toFixed(2)}</span>
                    </div>
                  </div>
                {/each}
              </div>
            </div>

            <button class="w-full p-2 border border-amber text-amber mono text-[10px] uppercase tracking-widest hover:bg-amber-dim transition-colors" on:click={() => goto($controlRoom.systemMap?.boss.route ?? "/command")}>
              ACCESS COMMAND PROTOCOL
            </button>
          </div>
        {:else if selectedNode && $controlRoom.selectedAgent?.agent_id === selectedNode.id}
          <div class="space-y-6">
            <p class="text-xs text-ink-secondary leading-relaxed">{selectedNode.summary}</p>

            <div class="grid grid-cols-2 gap-4 border-y border-subtle py-4">
              <div class="status-metric">
                <span class="status-metric__label">HEALTH</span>
                <span class="status-metric__value" class:text-emerald={selectedNode.status === 'healthy'} class:text-amber={selectedNode.status === 'warning'} class:text-crimson={selectedNode.status === 'critical'}>
                  {selectedNode.status.toUpperCase()}
                </span>
              </div>
              <div class="status-metric">
                <span class="status-metric__label">SYNCED</span>
                <span class="status-metric__value mono text-[10px]">{formatTime(selectedNode.updated_at)}</span>
              </div>
            </div>

            {#if selectedNode.warnings.length}
              <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] leading-relaxed">
                <div class="flex items-center gap-2 mb-1 font-bold">
                  <Activity size={10} />
                  <span>WARNING DETECTED</span>
                </div>
                {#each selectedNode.warnings as warning}
                  <p>• {warning}</p>
                {/each}
              </div>
            {/if}

            <div class="space-y-3">
              <span class="status-metric__label">RECENT PULSES</span>
              <div class="space-y-2">
                {#each $controlRoom.selectedAgent.runs.slice(0, 3) as run}
                  <div class="p-2 bg-obsidian-700 border border-subtle flex justify-between items-center">
                    <span class="mono text-[10px]">{run.status}</span>
                    <span class="mono text-[10px] opacity-40">{formatTime(String(run.finished_at ?? run.started_at ?? ""))}</span>
                  </div>
                {/each}
              </div>
            </div>

            <div class="space-y-3">
              <span class="status-metric__label">ACTIVE SIGNALS</span>
              <div class="grid grid-cols-2 gap-2">
                {#each $controlRoom.selectedAgent.signals.slice(0, 4) as signal}
                  <div class="p-2 bg-obsidian-900 border border-subtle flex justify-between items-center">
                    <span class="mono text-[10px] font-bold">{signal.ticker}</span>
                    <span class="mono text-[10px] text-emerald">{Number(signal.score ?? 0).toFixed(2)}</span>
                  </div>
                {/each}
              </div>
            </div>
          </div>
        {:else}
          <div class="flex flex-col items-center justify-center py-20 text-ink-dim gap-2">
            <Layers size={24} strokeWidth={1} />
            <span class="mono text-[9px] uppercase tracking-widest">Awaiting Selection</span>
          </div>
        {/if}
      </Panel>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Panel eyebrow="SYSTEM OUTPUTS" title="Artifact Registry">
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {#each $controlRoom.systemMap.artifacts as artifact}
            <button class="p-4 bg-obsidian-800 border border-subtle text-left group hover:border-emerald transition-all" on:click={() => goto(artifact.route)}>
              <div class="status-metric mb-2">
                <span class="status-metric__label">{artifact.label}</span>
                <span class="status-metric__value mono text-lg group-hover:text-emerald">{artifact.value}</span>
              </div>
              <p class="text-[9px] text-ink-dim uppercase leading-tight truncate">{artifact.caption}</p>
            </button>
          {/each}
        </div>
      </Panel>

      <Panel eyebrow="TEMPORAL SCHEDULER" title="Next Cron Sequence">
        <div class="space-y-2">
          {#each $controlRoom.systemMap.schedule as item}
            <div class="p-3 bg-obsidian-800 border border-subtle flex justify-between items-center hover:bg-obsidian-700 transition-colors">
              <div class="flex items-center gap-3">
                <Clock size={14} class="text-emerald opacity-50" />
                <span class="mono text-xs font-medium uppercase">{item.label}</span>
              </div>
              <div class="flex items-center gap-4">
                <span class="mono text-xs text-emerald">{formatTime(item.value)}</span>
                <span class="text-[9px] px-2 py-0-5 border border-subtle rounded-full uppercase text-ink-dim">{item.pending ? "PENDING" : "SCHEDULED"}</span>
              </div>
            </div>
          {/each}
        </div>
      </Panel>
    </div>
  </div>
{/if}

<style>
  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
  .space-y-2 > * + * { margin-top: 0.5rem; }
  .space-y-3 > * + * { margin-top: 0.75rem; }
  .space-y-6 > * + * { margin-top: 1.5rem; }

  .items-end { align-items: flex-end; }
  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .border-y { border-top: 1px solid var(--border-subtle); border-bottom: 1px solid var(--border-subtle); }
  .pb-6 { padding-bottom: 1.5rem; }
  .py-4 { padding-top: 1rem; padding-bottom: 1rem; }
  .py-20 { padding-top: 5rem; padding-bottom: 5rem; }
  .px-2 { padding-left: 0.5rem; padding-right: 0.5rem; }
  .py-0-5 { padding-top: 0.125rem; padding-bottom: 0.125rem; }

  .tracking-tight { letter-spacing: -0.025em; }
  .max-w-xl { max-width: 36rem; }
  .w-full { width: 100%; }
  .rounded-full { border-radius: 9999px; }
  .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .opacity-50 { opacity: 0.5; }
  .opacity-40 { opacity: 0.4; }
</style>
