<script lang="ts">
  import { onMount } from "svelte";
  import Panel from "$components/Panel.svelte";
  import { api, type ArtifactFile, type ArtifactFileDetail } from "$lib/api";
  import { controlRoom } from "$lib/control-room";
  import { formatDateTime, formatTime } from "$lib/format";
  import { Settings2, ShieldCheck, Zap, HardDrive, FileCode, Search, MessageSquare, Clock } from "@lucide/svelte";

  let files: ArtifactFile[] = [];
  let selected: ArtifactFileDetail | null = null;
  let searchQuery = "";

  onMount(async () => {
    await controlRoom.ensureConfig();
    const payload = await api.configFiles();
    files = payload;
    const first = payload.find((item) => item.exists);
    if (first) {
      selected = await api.configFileDetail(first.relative_path);
    }
  });

  async function selectFile(relativePath: string) {
    selected = await api.configFileDetail(relativePath);
  }

  $: filteredFiles = files.filter(f =>
    f.relative_path.toLowerCase().includes(searchQuery.toLowerCase())
  );

  $: marketSettings = ($controlRoom.config?.settings.market as Record<string, unknown> | undefined) ?? {};
</script>

{#if !$controlRoom.config || !$controlRoom.overview}
  <div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Accessing Configuration Matrix...</div>
  </div>
{:else}
  <div class="space-y-6">
    <section class="flex justify-between items-end border-b border-subtle pb-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 text-emerald">
          <Settings2 size={14} />
          <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">System Configuration</span>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">Desk <span class="text-emerald">Controls</span></h1>
        <p class="text-ink-secondary text-sm max-w-xl">Environment parameters, provider health, and static artifacts.</p>
      </div>

      <div class="flex gap-4">
        {#each Object.entries($controlRoom.overview.provider_health) as [name, data]}
          {@const payload = data as { status: string }}
          <div class="status-metric text-right">
            <span class="status-metric__label uppercase">{name}</span>
            <span class="status-metric__value mono text-xs uppercase" class:text-emerald={payload.status === 'READY' || payload.status === 'OK'} class:text-amber={payload.status !== 'READY' && payload.status !== 'OK'}>
              {payload.status ?? "UNKNOWN"}
            </span>
          </div>
        {/each}
      </div>
    </section>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <Panel eyebrow="RUNTIME" title="Execution Gates" tone="emerald">
        <div class="space-y-4">
          <div class="grid grid-cols-1 gap-3">
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">AUTONOMY</span>
              <span class="mono text-xs font-bold" class:text-amber={$controlRoom.config.runtime_state.autonomy_paused}>
                {$controlRoom.config.runtime_state.autonomy_paused ? "PAUSED" : "ACTIVE"}
              </span>
            </div>
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">ENTRIES</span>
              <span class="mono text-xs font-bold" class:text-crimson={$controlRoom.config.runtime_state.entries_blocked}>
                {$controlRoom.config.runtime_state.entries_blocked ? "BLOCKED" : "OPEN"}
              </span>
            </div>
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">EXITS ONLY</span>
              <span class="mono text-xs font-bold" class:text-amber={$controlRoom.config.runtime_state.exits_only}>
                {$controlRoom.config.runtime_state.exits_only ? "YES" : "NO"}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2 opacity-40">
            <Clock size={10} />
            <span class="text-[9px] uppercase mono">UPDATED: {formatTime($controlRoom.config.runtime_state.updated_at)}</span>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="THRESHOLDS" title="Risk Parameters" tone="amber">
        <div class="grid grid-cols-1 gap-3">
          <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">CONVICTION</span>
            <span class="mono text-xs font-bold text-amber">{String(marketSettings.conviction_threshold ?? "--")}</span>
          </div>
          <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">MAX POS %</span>
            <span class="mono text-xs font-bold">{String(marketSettings.max_single_position_pct ?? "--")}%</span>
          </div>
          <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">MAX SECT %</span>
            <span class="mono text-xs font-bold">{String(marketSettings.max_sector_exposure_pct ?? "--")}%</span>
          </div>
          <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">MIN CASH %</span>
            <span class="mono text-xs font-bold">{String(marketSettings.min_cash_pct ?? "--")}%</span>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="COMMUNICATIONS" title="Active Desk Notes">
        <div class="space-y-3">
          {#if $controlRoom.config.active_messages.length}
            {#each $controlRoom.config.active_messages.slice(0, 4) as message}
              <div class="p-3 bg-obsidian-700 border border-subtle space-y-2 group hover:border-emerald transition-colors">
                <div class="flex justify-between items-center">
                  <span class="mono text-[10px] font-bold text-emerald">{String(message.scope).toUpperCase()}</span>
                  <span class="text-[9px] text-ink-dim uppercase">{String(message.status)}</span>
                </div>
                <p class="text-xs text-ink-secondary leading-relaxed">{String(message.raw_text)}</p>
              </div>
            {/each}
          {:else}
            <div class="flex flex-col items-center justify-center py-12 text-ink-dim gap-2 border border-dashed border-subtle">
              <MessageSquare size={20} strokeWidth={1} />
              <span class="mono text-[9px] uppercase tracking-widest">No Active Directives</span>
            </div>
          {/if}
        </div>
      </Panel>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[320px,1fr] gap-6 items-start">
      <Panel eyebrow="ARTIFACTS" title="Static Files" tone="emerald">
        <div class="space-y-4">
          <div class="relative">
            <input
              type="text"
              bind:value={searchQuery}
              placeholder="Filter artifacts..."
              class="w-full bg-obsidian-900 border border-subtle p-2 pl-8 mono text-[10px] uppercase outline-none focus:border-emerald transition-colors"
            />
            <Search size={12} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-dim" />
          </div>

          <div class="space-y-1 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
            {#each filteredFiles as file}
              <button
                class="w-full p-3 bg-obsidian-700 border border-subtle text-left group transition-all"
                class:border-emerald={selected?.relative_path === file.relative_path}
                class:bg-emerald-dim={selected?.relative_path === file.relative_path}
                on:click={() => file.exists && selectFile(file.relative_path)}
                disabled={!file.exists}
              >
                <div class="flex items-center gap-3">
                  <FileCode size={14} class={selected?.relative_path === file.relative_path ? 'text-emerald' : 'text-ink-dim'} />
                  <div class="flex flex-col min-w-0">
                    <span class="mono text-[10px] font-bold truncate" class:text-emerald={selected?.relative_path === file.relative_path}>
                      {file.relative_path.split('/').pop()}
                    </span>
                    <span class="text-[8px] text-ink-dim uppercase tracking-tighter" class:text-emerald={file.exists} class:text-crimson={!file.exists}>
                      {file.exists ? "NODE_ACTIVE" : "NODE_MISSING"}
                    </span>
                  </div>
                </div>
                {#if file.modified_at}
                  <div class="mt-2 text-right opacity-40">
                    <span class="mono text-[9px]">{formatTime(file.modified_at)}</span>
                  </div>
                {/if}
              </button>
            {/each}
          </div>
        </div>
      </Panel>

      <Panel eyebrow="MATRIX PREVIEW" title={selected?.relative_path || "Buffer View"} tone={selected ? "emerald" : ""}>
        {#if selected}
          <div class="relative group">
            <pre class="bg-obsidian-900 border border-subtle p-6 mono text-[11px] leading-relaxed text-emerald/80 overflow-x-auto max-h-[70vh] custom-scrollbar selection:bg-emerald selection:text-obsidian-900">{selected.preview}</pre>
            <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <div class="px-2 py-1 bg-emerald text-obsidian-900 mono text-[8px] font-bold uppercase">READ ONLY DATA</div>
            </div>
          </div>
        {:else}
          <div class="flex flex-col items-center justify-center py-40 text-ink-dim gap-4 border border-dashed border-subtle">
            <HardDrive size={32} strokeWidth={1} />
            <span class="mono text-[10px] uppercase tracking-[0.3em]">Select Configuration Node</span>
          </div>
        {/if}
      </Panel>
    </div>
  </div>
{/if}

<style>
  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
  .space-y-2 > * + * { margin-top: 0.5rem; }
  .space-y-3 > * + * { margin-top: 0.75rem; }
  .space-y-4 > * + * { margin-top: 1rem; }
  .space-y-6 > * + * { margin-top: 1.5rem; }

  .items-center { align-items: center; }
  .items-end { align-items: flex-end; }
  .justify-center { justify-content: center; }
  .justify-between { justify-content: space-between; }

  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .pb-6 { padding-bottom: 1.5rem; }
  .min-h-\[60vh\] { min-height: 60vh; }
  .max-w-xl { max-width: 36rem; }

  .tracking-tight { letter-spacing: -0.025em; }
  .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: var(--obsidian-600);
  }
</style>
