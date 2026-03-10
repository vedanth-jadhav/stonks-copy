<script lang="ts">
  import { onMount } from "svelte";
  import Panel from "$components/Panel.svelte";
  import Sparkline from "$components/Sparkline.svelte";
  import { controlRoom } from "$lib/control-room";
  import { formatCurrency, formatDateTime, formatTime } from "$lib/format";
  import { Gauge, Send, Play, Pause, AlertTriangle, Zap, Cpu, Activity, Clock } from "@lucide/svelte";

  let message = "";
  let busyAction = "";
  let actionError = "";
  const jobButtons = [
    { id: "morning-pipeline", label: "Morning Pipeline", detail: "09:30" },
    { id: "midday-pipeline", label: "Midday Pipeline", detail: "11:30" },
    { id: "afternoon-pipeline", label: "Afternoon Pipeline", detail: "13:00" },
    { id: "risk-final-pipeline", label: "Risk-Final Pipeline", detail: "14:30" },
    { id: "signal-backfill", label: "Signal Backfill", detail: "16:00" },
    { id: "weekly-report", label: "Weekly Report", detail: "Fri 16:30" },
    { id: "portfolio-history-repair", label: "Portfolio Repair", detail: "Manual" },
    { id: "holiday-sync", label: "Holiday Sync", detail: "08:16" },
    { id: "pairs-revalidation", label: "Pairs Revalidation", detail: "Sun 09:00" },
  ];

  onMount(() => {
    void Promise.all([controlRoom.ensurePortfolio(), controlRoom.ensureRuns()]);
  });

  $: sparkline = $controlRoom.portfolio?.marks.map((row) => row.portfolio_value).reverse() ?? [];

  async function runAction(id: string, action: () => Promise<void>) {
    busyAction = id;
    actionError = "";
    try {
      await action();
    } catch (error) {
      actionError = error instanceof Error ? error.message : "Action failed.";
    } finally {
      busyAction = "";
    }
  }
</script>

{#if !$controlRoom.overview || !$controlRoom.portfolio}
  <div class="flex flex-col items-center justify-center min-h-[60vh] gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.2em] text-emerald opacity-50 uppercase">Securing Command Uplink...</div>
  </div>
{:else}
  <div class="space-y-6">
    <section class="flex justify-between items-end border-b border-subtle pb-6">
      <div class="space-y-1">
        <div class="flex items-center gap-2 text-emerald">
          <Gauge size={14} />
          <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Manual Override Surface</span>
        </div>
        <h1 class="text-3xl font-bold tracking-tight">Operator <span class="text-emerald">Deck</span></h1>
        <p class="text-ink-secondary text-sm max-w-xl">Direct instruction injection, manual job triggering, and autonomy control.</p>
      </div>

      <div class="w-64 h-16 opacity-80">
        <Sparkline values={sparkline} />
      </div>
    </section>

    <div class="grid grid-cols-1 lg-grid-cols-command gap-6 items-start">
      <Panel eyebrow="INSTRUCTION INJECTION" title="Direct Desk Note" tone="emerald">
        <div class="space-y-4">
          <textarea
            class="w-full h-32 bg-obsidian-900 border border-subtle p-4 mono text-xs text-emerald focus:border-emerald focus:ring-1 focus:ring-emerald outline-none resize-none"
            bind:value={message}
            placeholder="[SYSTEM_CMD]: Enter override parameters (e.g., 'restrict INFY exposure')"
          ></textarea>

          <div class="flex justify-between items-center">
            <div class="flex gap-2">
              {#if $controlRoom.overview.runtime_state.autonomy_paused}
                <button
                  class="flex items-center gap-2 px-4 py-2 bg-emerald-dim border border-emerald text-emerald mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald/20 transition-all"
                  disabled={busyAction !== ""}
                  on:click={() => runAction("resume", () => controlRoom.resumeAutonomy())}
                >
                  <Play size={12} />
                  RESUME AUTONOMY
                </button>
              {:else}
                <button
                  class="flex items-center gap-2 px-4 py-2 bg-amber-dim border border-amber text-amber mono text-[10px] font-bold uppercase tracking-widest hover:bg-amber/20 transition-all"
                  disabled={busyAction !== ""}
                  on:click={() => runAction("pause", () => controlRoom.pauseAutonomy())}
                >
                  <Pause size={12} />
                  HALT AUTONOMY
                </button>
              {/if}
            </div>

            <button
              class="flex items-center gap-2 px-6 py-2 bg-emerald text-obsidian-900 mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all"
              disabled={busyAction !== "" || !message.trim()}
              on:click={() => runAction("send-note", async () => { await controlRoom.createDeskMessage(message); message = ""; })}
            >
              <Send size={12} />
              INJECT NOTE
            </button>
          </div>

          {#if actionError}
            <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] flex items-center gap-2">
              <AlertTriangle size={12} />
              <span class="mono uppercase tracking-widest">{actionError}</span>
            </div>
          {/if}
        </div>
      </Panel>

      <Panel eyebrow="JOB SEQUENCING" title="Manual Triggers">
        <div class="grid grid-cols-2 gap-3">
          {#each jobButtons as job}
            <button
              class="p-3 bg-obsidian-700 border border-subtle text-left group hover:border-emerald transition-all"
              disabled={busyAction !== ""}
              on:click={() => runAction(job.id, () => controlRoom.runJob(job.id))}
            >
              <div class="flex flex-col">
                <span class="mono text-[10px] font-bold text-emerald group-hover:text-emerald-glow">{job.label}</span>
                <span class="text-[9px] text-ink-dim uppercase mt-1 tracking-tighter">{job.detail}</span>
              </div>
              {#if busyAction === job.id}
                <div class="mt-2 h-0.5 w-full bg-emerald/20 overflow-hidden">
                  <div class="h-full bg-emerald animate-[shimmer_1s_infinite]"></div>
                </div>
              {/if}
            </button>
          {/each}
        </div>
      </Panel>
    </div>

    <div class="grid grid-cols-1 md-grid-cols-3 gap-6">
      <Panel eyebrow="RUNTIME GATE" title="Risk Sentinel" tone="amber">
        <div class="space-y-4">
          <div class="grid grid-cols-1 gap-3">
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">AUTONOMY</span>
              <span class="mono text-xs font-bold" class:text-emerald={!$controlRoom.overview.runtime_state.autonomy_paused} class:text-amber={$controlRoom.overview.runtime_state.autonomy_paused}>
                {$controlRoom.overview.runtime_state.autonomy_paused ? "PAUSED" : "ACTIVE"}
              </span>
            </div>
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">ENTRIES</span>
              <span class="mono text-xs font-bold" class:text-emerald={!$controlRoom.overview.runtime_state.entries_blocked} class:text-crimson={$controlRoom.overview.runtime_state.entries_blocked}>
                {$controlRoom.overview.runtime_state.entries_blocked ? "BLOCKED" : "ENABLED"}
              </span>
            </div>
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">EXITS ONLY</span>
              <span class="mono text-xs font-bold" class:text-amber={$controlRoom.overview.runtime_state.exits_only}>
                {$controlRoom.overview.runtime_state.exits_only ? "YES" : "NO"}
              </span>
            </div>
          </div>
          <div class="flex items-center gap-2 opacity-40">
            <Clock size={10} />
            <span class="text-[9px] uppercase mono">LAST SYNC: {formatTime($controlRoom.overview.runtime_state.updated_at)}</span>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="CAPITAL STATE" title="Equity Profile">
        <div class="space-y-4">
          <div class="grid grid-cols-1 gap-3">
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">NAV</span>
              <span class="mono text-xs font-bold text-emerald">{formatCurrency($controlRoom.overview.portfolio.portfolio_value)}</span>
            </div>
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">DEPLOYED</span>
              <span class="mono text-xs font-bold">{formatCurrency($controlRoom.overview.portfolio.total_deployed)}</span>
            </div>
            <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">OPEN NODES</span>
              <span class="mono text-xs font-bold">{$controlRoom.overview.portfolio.open_positions}</span>
            </div>
          </div>
          <div class="flex items-center gap-2 opacity-40">
            <Activity size={10} />
            <span class="text-[9px] uppercase mono">EXPOSURE: {formatCurrency($controlRoom.overview.portfolio.total_market_value)}</span>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="EXECUTION TAPE" title="Recent Pulses">
        <div class="space-y-2">
          {#each $controlRoom.runs.slice(0, 5) as run}
            <div class="p-3 bg-obsidian-700 border border-subtle flex justify-between items-center group hover:border-emerald transition-colors">
              <div class="flex flex-col">
                <span class="mono text-[10px] font-bold truncate max-w-[120px]">{String(run.name ?? run.job_name).toUpperCase()}</span>
                <span class="text-[8px] text-ink-dim uppercase mt-1">{formatTime(String(run.started_at ?? ""))}</span>
              </div>
              <span class="mono text-[9px] px-2 py-0-5 border border-subtle rounded-full uppercase" class:text-emerald={run.status === 'success'} class:text-amber={run.status === 'running'}>
                {String(run.status ?? "IDLE")}
              </span>
            </div>
          {/each}
        </div>
      </Panel>
    </div>
  </div>
{/if}

<style>
  @keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
  }

  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
  .space-y-2 > * + * { margin-top: 0.5rem; }
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
</style>
