<script lang="ts">
  import { onMount } from "svelte";
  import Panel from "$components/Panel.svelte";
  import { api } from "$lib/api";
  import { controlRoom } from "$lib/control-room";
  import { MemoryStick, Search, Zap, Layers, History, Database } from "@lucide/svelte";

  let query = "caution regime";
  let results: Array<Record<string, any>> = [];
  let searching = false;

  onMount(() => {
    void controlRoom.ensureMemory();
  });

  async function search() {
    if (!query.trim()) return;
    searching = true;
    try {
      const payload = await api.memorySearch(query);
      results = payload.results;
    } finally {
      searching = false;
    }
  }
</script>

{#if !$controlRoom.memory}
  <div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Loading Memory Graph...</div>
  </div>
{:else}
  <div class="space-y-6">
    <section class="flex justify-between items-end border-b border-subtle pb-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 text-emerald">
          <MemoryStick size={14} />
          <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Neural Retrieval Desk</span>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">System <span class="text-emerald">Memory</span></h1>
        <p class="text-ink-secondary text-sm max-w-xl">Semantic search across the knowledge graph and historical episode retrieval.</p>
      </div>

      <div class="flex gap-4">
        <div class="status-metric text-right">
          <span class="status-metric__label">GRAPH NODES</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.memory?.nodes.length ?? 0}</span>
        </div>
        <div class="status-metric text-right">
          <span class="status-metric__label">EDGES</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.memory?.edges.length ?? 0}</span>
        </div>
      </div>
    </section>

    <Panel eyebrow="SEMANTIC SEARCH" title="Knowledge Retrieval" tone="emerald">
      <form class="flex gap-4" on:submit|preventDefault={search}>
        <div class="relative flex-1">
          <input
            type="text"
            bind:value={query}
            placeholder="Search the neural graph (e.g., 'market regime shifts')"
            class="w-full bg-obsidian-900 border border-subtle p-3 pl-10 mono text-xs text-emerald outline-none focus:border-emerald transition-colors"
          />
          <Search size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-ink-dim" />
        </div>
        <button
          type="submit"
          disabled={searching}
          class="px-8 bg-emerald text-obsidian-900 mono text-xs font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all"
        >
          {searching ? "FETCHING..." : "QUERY"}
        </button>
      </form>
    </Panel>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
      <Panel eyebrow="SEARCH RESULTS" title="Relevant Episodes">
        <div class="space-y-3">
          {#if results.length}
            {#each results as result}
              <div class="p-4 bg-obsidian-700 border border-subtle space-y-3 group hover:border-emerald transition-colors">
                <div class="flex justify-between items-center">
                  <span class="mono text-[10px] font-bold text-emerald">{String(result.ref_id).toUpperCase()}</span>
                  <span class="text-[9px] text-ink-dim uppercase tracking-widest">{String(result.node_type)}</span>
                </div>
                <p class="text-xs text-ink-secondary leading-relaxed">{String(result.content)}</p>
              </div>
            {/each}
          {:else}
            <div class="flex flex-col items-center justify-center py-20 text-ink-dim gap-4 border border-dashed border-subtle">
              <Layers size={24} strokeWidth={1} />
              <span class="mono text-[9px] uppercase tracking-widest">Execute query to retrieve data</span>
            </div>
          {/if}
        </div>
      </Panel>

      <Panel eyebrow="GRAPH TAPE" title="Recent Node Entries">
        <div class="space-y-3">
          {#each ($controlRoom.memory?.nodes ?? []).slice(0, 8) as node}
            <div class="p-3 bg-obsidian-800 border border-subtle flex gap-4 group hover:border-emerald transition-colors">
              <div class="flex-shrink-0 mt-1">
                <Database size={14} class="text-ink-dim group-hover:text-emerald" />
              </div>
              <div class="flex flex-col min-w-0">
                <div class="flex justify-between items-center mb-1">
                  <span class="mono text-[10px] font-bold text-emerald">{String(node.ref_id).toUpperCase()}</span>
                  <span class="text-[8px] text-ink-dim uppercase">{String(node.node_type)}</span>
                </div>
                <p class="text-[11px] text-ink-secondary leading-normal truncate">{String(node.content)}</p>
              </div>
            </div>
          {/each}
          {#if !($controlRoom.memory?.nodes.length)}
             <div class="text-center py-20 text-ink-dim mono text-[10px] uppercase tracking-widest">No entries in buffer</div>
          {/if}
        </div>
      </Panel>
    </div>
  </div>
{/if}

<style>
  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
  .space-y-3 > * + * { margin-top: 0.75rem; }
  .space-y-6 > * + * { margin-top: 1.5rem; }

  .flex { display: flex; }
  .flex-col { flex-direction: column; }
  .flex-1 { flex: 1 1 0%; }
  .items-center { align-items: center; }
  .items-end { align-items: flex-end; }
  .justify-center { justify-content: center; }
  .justify-between { justify-content: space-between; }

  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .border-dashed { border-style: dashed; }
  .pb-6 { padding-bottom: 1.5rem; }
  .p-3 { padding: 0.75rem; }
  .p-4 { padding: 1rem; }
  .pl-10 { padding-left: 2.5rem; }
  .px-8 { padding-left: 2rem; padding-right: 2rem; }
  .py-20 { padding-top: 5rem; padding-bottom: 5rem; }

  .min-h-\[60vh\] { min-height: 60vh; }
  .max-w-xl { max-width: 36rem; }
  .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
