<script lang="ts">
  import Panel from "$components/Panel.svelte";
  import { formatDateTime, formatTime } from "$lib/format";
  import type { ArtifactFile, ArtifactFileDetail } from "$lib/api";
  import { FileCode, Clock, HardDrive, Search, FileText } from "@lucide/svelte";

  export let title = "";
  export let subtitle = "";
  export let files: ArtifactFile[] = [];
  export let selected: ArtifactFileDetail | null = null;
  export let emptyLabel = "No files.";
  export let onSelect: (relativePath: string) => void;

  let searchQuery = "";

  $: filteredFiles = files.filter(f =>
    f.relative_path.toLowerCase().includes(searchQuery.toLowerCase())
  );
</script>

<div class="grid grid-cols-1 lg-grid-cols-workbench gap-6 items-start">
  <Panel eyebrow={title} title="Artifact Index" tone="emerald">
    <div class="space-y-4">
      <div class="relative">
        <input
          type="text"
          bind:value={searchQuery}
          placeholder="Filter buffer..."
          class="w-full bg-obsidian-900 border border-subtle p-2 pl-8 mono text-[10px] uppercase outline-none focus:border-emerald transition-colors"
        />
        <Search size={12} class="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-dim" />
      </div>

      <div class="space-y-1 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
        {#if filteredFiles.length}
          {#each filteredFiles as file}
            <button
              class="w-full p-3 bg-obsidian-700 border border-subtle text-left group transition-all"
              class:border-emerald={selected?.relative_path === file.relative_path}
              class:bg-emerald-dim={selected?.relative_path === file.relative_path}
              on:click={() => onSelect(file.relative_path)}
            >
              <div class="flex items-center gap-3">
                <FileCode size={14} class={selected?.relative_path === file.relative_path ? 'text-emerald' : 'text-ink-dim'} />
                <div class="flex flex-col min-w-0">
                  <span class="mono text-[10px] font-bold truncate" class:text-emerald={selected?.relative_path === file.relative_path}>
                    {file.relative_path.split('/').pop()}
                  </span>
                  <span class="text-[8px] text-ink-dim uppercase truncate">{file.relative_path}</span>
                </div>
              </div>
              <div class="mt-2 flex justify-between items-center opacity-40">
                <span class="mono text-[9px]">{file.size_bytes} B</span>
                <span class="mono text-[9px]">{formatTime(file.modified_at)}</span>
              </div>
            </button>
          {/each}
        {:else}
          <div class="py-12 text-center text-ink-dim mono text-[10px] uppercase tracking-widest border border-dashed border-subtle">
            {emptyLabel}
          </div>
        {/if}
      </div>
    </div>
  </Panel>

  <Panel eyebrow={title} title={subtitle || "Buffer Preview"} tone={selected ? "emerald" : ""}>
    {#if selected}
      <div class="space-y-4">
        <div class="flex justify-between items-center border-b border-subtle pb-4">
          <div class="flex items-center gap-3">
            <FileText size={16} class="text-emerald" />
            <div class="flex flex-col">
              <span class="mono text-xs font-bold text-emerald">{selected.relative_path}</span>
            </div>
          </div>
          <div class="flex gap-4">
            <div class="status-metric text-right">
              <span class="status-metric__label">SIZE</span>
              <span class="status-metric__value mono text-xs">{selected.size_bytes}</span>
            </div>
            <div class="status-metric text-right">
              <span class="status-metric__label">MODIFIED</span>
              <span class="status-metric__value mono text-xs">{formatTime(selected.modified_at)}</span>
            </div>
          </div>
        </div>

        <div class="relative group">
          <pre class="bg-obsidian-900 border border-subtle p-6 mono text-[11px] leading-relaxed text-emerald/80 overflow-x-auto max-h-[70vh] custom-scrollbar selection:bg-emerald selection:text-obsidian-900">{selected.preview}</pre>
          <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div class="px-2 py-1 bg-emerald text-obsidian-900 mono text-[8px] font-bold uppercase">Read Only Buffer</div>
          </div>
        </div>
      </div>
    {:else}
      <div class="flex flex-col items-center justify-center py-40 text-ink-dim gap-4 border border-dashed border-subtle">
        <HardDrive size={32} strokeWidth={1} />
        <span class="mono text-[10px] uppercase tracking-[0.3em]">Initialize Buffer Selection</span>
      </div>
    {/if}
  </Panel>
</div>

<style>
  .custom-scrollbar::-webkit-scrollbar {
    width: 4px;
  }
  .custom-scrollbar::-webkit-scrollbar-thumb {
    background: var(--obsidian-600);
  }
</style>
