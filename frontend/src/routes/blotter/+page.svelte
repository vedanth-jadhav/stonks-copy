<script lang="ts">
  import { onMount } from "svelte";
  import LedgerTable from "$components/LedgerTable.svelte";
  import Panel from "$components/Panel.svelte";
  import { controlRoom } from "$lib/control-room";
  import { formatCurrency, formatDateTime, formatTime } from "$lib/format";
  import { ClipboardList, Activity, Zap, History, Target, Shield } from "@lucide/svelte";

  onMount(() => {
    void Promise.all([controlRoom.ensurePortfolio(), controlRoom.ensureAgents()]);
  });
</script>

{#if !$controlRoom.portfolio}
  <div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Accessing Audit Vault...</div>
  </div>
{:else}
  <div class="space-y-6">
    <section class="flex justify-between items-end border-b border-subtle pb-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 text-emerald">
          <ClipboardList size={14} />
          <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Execution Ledger</span>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">System <span class="text-emerald">Blotter</span></h1>
        <p class="text-ink-secondary text-sm max-w-xl">Audit trails, decision sequences, and instruction validation.</p>
      </div>

      <div class="flex gap-4">
        <div class="status-metric text-right">
          <span class="status-metric__label">DECISIONS</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.portfolio.decisions.length}</span>
        </div>
        <div class="status-metric text-right">
          <span class="status-metric__label">ORDERS</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.portfolio.orders.length}</span>
        </div>
        <div class="status-metric text-right">
          <span class="status-metric__label">FILLS</span>
          <span class="status-metric__value mono text-emerald">{$controlRoom.portfolio.fills.length}</span>
        </div>
      </div>
    </section>

    <div class="grid grid-cols-1 md-grid-cols-3 gap-6">
      <Panel eyebrow="COMMAND PROTOCOL" title="Recent Decisions" tone="emerald">
        <div class="space-y-3">
          {#each $controlRoom.portfolio.decisions.slice(0, 5) as decision}
            <div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-start group hover:border-emerald transition-colors">
              <div class="flex flex-col">
                <span class="mono text-xs font-bold text-emerald">{String(decision.ticker)}</span>
                <span class="text-[9px] text-ink-dim uppercase mt-1">{formatTime(String(decision.created_at ?? ""))}</span>
              </div>
              <div class="text-right">
                <span class="mono text-xs font-bold uppercase">{String(decision.decision)}</span>
                <div class="text-[9px] text-ink-dim mono">CONF: {Number(decision.confidence ?? 0).toFixed(2)}</div>
              </div>
            </div>
          {/each}
        </div>
      </Panel>

      <Panel eyebrow="INSTRUCTION FLOW" title="Pending Orders">
        <div class="space-y-3">
          {#each $controlRoom.portfolio.orders.slice(0, 5) as order}
            <div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-start group hover:border-amber transition-colors">
              <div class="flex flex-col">
                <span class="mono text-xs font-bold text-amber">{String(order.ticker)}</span>
                <span class="text-[9px] text-ink-dim uppercase mt-1">{formatTime(String(order.created_at ?? ""))}</span>
              </div>
              <div class="text-right">
                <span class="mono text-xs font-bold">{String(order.shares ?? 0)} SH</span>
                <div class="text-[9px] text-ink-dim uppercase tracking-widest">{String(order.decision)}</div>
              </div>
            </div>
          {/each}
        </div>
      </Panel>

      <Panel eyebrow="EXECUTION LOG" title="Matched Fills">
        <div class="space-y-3">
          {#each $controlRoom.portfolio.fills.slice(0, 5) as fill}
            <div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-start group hover:border-emerald transition-colors">
              <div class="flex flex-col">
                <span class="mono text-xs font-bold text-emerald">{String(fill.ticker)}</span>
                <span class="text-[9px] text-ink-dim uppercase mt-1">{String(fill.action)}</span>
              </div>
              <div class="text-right">
                <span class="mono text-xs font-bold">{formatCurrency(Number(fill.fill_price ?? 0))}</span>
                <div class="text-[9px] text-ink-dim mono">CHRG: {formatCurrency(Number(fill.charges ?? 0))}</div>
              </div>
            </div>
          {/each}
        </div>
      </Panel>
    </div>

    <div class="grid grid-cols-1 lg-grid-cols-blotter gap-6 items-start">
      <Panel eyebrow="AUDIT TABLE" title="Chronological Fills" tone="emerald">
        <LedgerTable
          rows={$controlRoom.portfolio.fills}
          columns={[
            { key: "ticker", label: "TICKER", type: "mono" },
            { key: "action", label: "ACTION" },
            { key: "fill_price", label: "PRICE", type: "mono" },
            { key: "charges", label: "CHARGES", type: "mono" },
            { key: "execution_type", label: "TYPE" },
          ]}
        />
      </Panel>

      <Panel eyebrow="VALIDATION" title="IC Diagnostics">
        <div class="space-y-4">
          <p class="text-[10px] text-ink-dim uppercase tracking-widest leading-relaxed">Cross-validation of agent signals against realized outcomes.</p>
          <div class="grid grid-cols-1 gap-3">
            {#each $controlRoom.agents as agent}
              <div class="p-3 bg-obsidian-900 border border-subtle group hover:border-emerald transition-colors">
                <div class="flex justify-between items-center mb-2">
                  <span class="mono text-[10px] font-bold text-emerald">{agent.agent_id.replace("agent_", "").toUpperCase()}</span>
                  <span class="text-[9px] text-ink-dim uppercase tracking-tighter">{String(agent.latest_run?.status ?? "idle")}</span>
                </div>
                <div class="grid grid-cols-3 gap-2">
                  <div class="status-metric">
                    <span class="status-metric__label">IC</span>
                    <span class="status-metric__value mono text-xs">{Number(agent.ic_snapshot.ic_value ?? 0).toFixed(3)}</span>
                  </div>
                  <div class="status-metric">
                    <span class="status-metric__label">WIN %</span>
                    <span class="status-metric__value mono text-xs">{agent.ic_snapshot.win_rate !== undefined ? `${(Number(agent.ic_snapshot.win_rate) * 100).toFixed(0)}%` : "--"}</span>
                  </div>
                  <div class="status-metric text-right">
                    <span class="status-metric__label">SMPL</span>
                    <span class="status-metric__value mono text-xs">{String(agent.ic_snapshot.sample_size ?? 0)}</span>
                  </div>
                </div>
              </div>
            {/each}
          </div>
        </div>
      </Panel>
    </div>
  </div>
{/if}

<style>
  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
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
</style>
