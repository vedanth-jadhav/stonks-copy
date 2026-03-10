<script lang="ts">
  import { onMount } from "svelte";
  import LedgerTable from "$components/LedgerTable.svelte";
  import Panel from "$components/Panel.svelte";
  import Sparkline from "$components/Sparkline.svelte";
  import { controlRoom } from "$lib/control-room";
  import { formatCurrency, formatDate, formatPercent, formatSignedPercent } from "$lib/format";
  import { TrendingUp, Wallet, Landmark, BarChart3, PieChart, Power, Zap } from "@lucide/svelte";

  let busyTicker = "";
  let actionError = "";

  onMount(() => {
    void controlRoom.ensurePortfolio();
  });

  async function forceExit(ticker: string) {
    busyTicker = ticker;
    actionError = "";
    try {
      await controlRoom.forceExit(ticker, 1);
    } catch (error) {
      actionError = error instanceof Error ? error.message : "Force exit failed.";
    } finally {
      busyTicker = "";
    }
  }
</script>

{#if !$controlRoom.portfolio}
  <div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Loading Capital Structures...</div>
  </div>
{:else}
  <div class="space-y-6">
    <section class="flex justify-between items-end border-b border-subtle pb-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 text-emerald">
          <TrendingUp size={14} />
          <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Capital Allocation Wall</span>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">Portfolio <span class="text-emerald">Dynamics</span></h1>
        <p class="text-ink-secondary text-sm max-w-xl">Asset exposure, equity curves, and direct execution overrides.</p>
      </div>

      <div class="w-64 h-16 opacity-80">
        <Sparkline values={$controlRoom.portfolio.marks.map((row) => row.portfolio_value).reverse()} />
      </div>
    </section>

    <div class="grid grid-cols-2 md-grid-cols-3 lg-grid-cols-5 gap-4">
      <div class="p-4 bg-obsidian-800 border border-subtle">
        <div class="status-metric">
          <span class="status-metric__label">NAV</span>
          <span class="status-metric__value mono text-xl">{formatCurrency($controlRoom.portfolio.snapshot.portfolio_value)}</span>
        </div>
      </div>
      <div class="p-4 bg-obsidian-800 border border-subtle">
        <div class="status-metric">
          <span class="status-metric__label">LIQUID CASH</span>
          <span class="status-metric__value mono text-xl">{formatCurrency($controlRoom.portfolio.snapshot.cash_balance)}</span>
        </div>
      </div>
      <div class="p-4 bg-obsidian-800 border border-subtle">
        <div class="status-metric">
          <span class="status-metric__label">EXPOSURE</span>
          <span class="status-metric__value mono text-xl">{formatCurrency($controlRoom.portfolio.snapshot.total_market_value)}</span>
        </div>
      </div>
      <div class="p-4 bg-obsidian-800 border border-subtle">
        <div class="status-metric">
          <span class="status-metric__label">UNREALIZED</span>
          <span class="status-metric__value mono text-xl" class:text-emerald={$controlRoom.portfolio.snapshot.total_unrealized_pnl >= 0} class:text-crimson={$controlRoom.portfolio.snapshot.total_unrealized_pnl < 0}>
            {formatCurrency($controlRoom.portfolio.snapshot.total_unrealized_pnl)}
          </span>
        </div>
      </div>
      <div class="p-4 bg-obsidian-800 border border-subtle">
        <div class="status-metric">
          <span class="status-metric__label">REALIZED</span>
          <span class="status-metric__value mono text-xl" class:text-emerald={$controlRoom.portfolio.snapshot.total_realized_pnl >= 0} class:text-crimson={$controlRoom.portfolio.snapshot.total_realized_pnl < 0}>
            {formatCurrency($controlRoom.portfolio.snapshot.total_realized_pnl)}
          </span>
        </div>
      </div>
    </div>

    <Panel eyebrow="INVENTORY" title="Live Holdings" tone="emerald">
      {#if actionError}
        <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-xs mb-4 uppercase tracking-widest">{actionError}</div>
      {/if}

      <div class="grid grid-cols-1 md-grid-cols-2 lg-grid-cols-3 xl-grid-cols-4 gap-4">
        {#if $controlRoom.portfolio.positions.length}
          {#each $controlRoom.portfolio.positions as position}
            <div class="p-4 bg-obsidian-700 border border-subtle space-y-4 hover:border-emerald transition-colors relative group">
              <div class="flex justify-between items-start">
                <div class="flex flex-col">
                  <span class="mono text-lg font-bold text-emerald">{position.ticker}</span>
                  <span class="text-[9px] text-ink-dim uppercase tracking-widest">{position.position_type} Position</span>
                </div>
                <button
                  class="p-2 border border-subtle text-ink-dim hover:text-crimson hover:border-crimson transition-all"
                  disabled={busyTicker !== ""}
                  on:click={() => forceExit(position.ticker)}
                  title="FORCE TERMINATION"
                >
                  <Power size={14} class={busyTicker === position.ticker ? 'animate-spin' : ''} />
                </button>
              </div>

              <div class="grid grid-cols-2 gap-4 border-y border-subtle/50 py-3">
                <div class="status-metric">
                  <span class="status-metric__label">QUANTITY</span>
                  <span class="status-metric__value mono text-sm">{position.shares}</span>
                </div>
                <div class="status-metric text-right">
                  <span class="status-metric__label">AVG PRICE</span>
                  <span class="status-metric__value mono text-sm">{formatCurrency(position.avg_entry_price)}</span>
                </div>
              </div>

              <div class="status-metric">
                <span class="status-metric__label">TOTAL EXPOSURE</span>
                <span class="status-metric__value mono text-sm">{formatCurrency(position.total_cost)}</span>
              </div>
            </div>
          {/each}
        {:else}
          <div class="col-span-full py-12 flex flex-col items-center justify-center text-ink-dim gap-2 border border-dashed border-subtle">
            <PieChart size={24} strokeWidth={1} />
            <span class="mono text-[10px] uppercase tracking-[0.2em]">Zero Inventory Detected</span>
          </div>
        {/if}
      </div>
    </Panel>

    <div class="grid grid-cols-1 lg-grid-cols-split gap-6">
      <Panel eyebrow="TEMPORAL SNAPSHOT" title="Current Regime" tone="amber">
        {#if $controlRoom.portfolio.marks[0]}
          {@const mark = $controlRoom.portfolio.marks[0]}
          <div class="space-y-4">
            <div class="p-4 bg-obsidian-900 border border-amber/20">
              <div class="status-metric">
                <span class="status-metric__label">ACTIVE REGIME</span>
                <span class="status-metric__value text-amber text-xl tracking-tight uppercase">
                  {String(mark.details.regime ?? "EQUILIBRIUM")}
                </span>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4 border-b border-subtle pb-4">
              <div class="status-metric">
                <span class="status-metric__label">ALPHA G.V.</span>
                <span class="status-metric__value mono" class:text-emerald={Number(mark.alpha_pct ?? 0) >= 0} class:text-crimson={Number(mark.alpha_pct ?? 0) < 0}>
                  {formatSignedPercent(mark.alpha_pct ?? 0)}
                </span>
              </div>
              <div class="status-metric text-right">
                <span class="status-metric__label">BENCHMARK</span>
                <span class="status-metric__value mono">
                  {formatPercent(mark.benchmark_return_pct ?? 0)}
                </span>
              </div>
            </div>

            <div class="space-y-3">
              <div class="flex justify-between items-center">
                <span class="status-metric__label">REALIZED (24H)</span>
                <span class="mono text-sm" class:text-emerald={Number(mark.realized_pnl_today ?? 0) >= 0} class:text-crimson={Number(mark.realized_pnl_today ?? 0) < 0}>
                  {formatCurrency(mark.realized_pnl_today ?? 0)}
                </span>
              </div>
              <div class="flex justify-between items-center">
                <span class="status-metric__label">AGGREGATE REALIZED</span>
                <span class="mono text-sm">
                  {formatCurrency(mark.total_realized_pnl ?? 0)}
                </span>
              </div>
              <div class="flex justify-between items-center">
                <span class="status-metric__label">DATA STAMP</span>
                <span class="mono text-[10px] text-ink-dim uppercase">
                  {formatDate(mark.mark_date)}
                </span>
              </div>
            </div>
          </div>
        {:else}
          <div class="py-20 text-center text-ink-dim mono text-[10px] uppercase tracking-widest">Awaiting First Mark</div>
        {/if}
      </Panel>

      <Panel eyebrow="AUDIT TRAIL" title="Marked Intervals">
        <LedgerTable
          rows={$controlRoom.portfolio.marks}
          columns={[
            { key: "mark_date", label: "DATE" },
            { key: "portfolio_value", label: "NAV", type: "mono" },
            { key: "realized_pnl_today", label: "REALIZED (24H)", type: "mono" },
            { key: "unrealized_pnl", label: "UNREALIZED", type: "mono" },
            { key: "alpha_pct", label: "ALPHA %", type: "mono" },
          ]}
        />
      </Panel>
    </div>
  </div>
{/if}

<style>
  .grid { display: grid; }
  .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
  .space-y-3 > * + * { margin-top: 0.75rem; }
  .space-y-4 > * + * { margin-top: 1rem; }
  .space-y-6 > * + * { margin-top: 1.5rem; }

  .items-center { align-items: center; }
  .items-end { align-items: flex-end; }
  .justify-center { justify-content: center; }
  .justify-between { justify-content: space-between; }

  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .border-y { border-top: 1px solid var(--border-subtle); border-bottom: 1px solid var(--border-subtle); }
  .border-dashed { border-style: dashed; }
  .pb-6 { padding-bottom: 1.5rem; }
  .py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
  .py-12 { padding-top: 3rem; padding-bottom: 3rem; }
  .py-20 { padding-top: 5rem; padding-bottom: 5rem; }

  .h-16 { height: 4rem; }
  .w-64 { width: 16rem; }
  .min-h-\[60vh\] { min-height: 60vh; }
  .max-w-xl { max-width: 36rem; }

  .tracking-tight { letter-spacing: -0.025em; }
</style>
