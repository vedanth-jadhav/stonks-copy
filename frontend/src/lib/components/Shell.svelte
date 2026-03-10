<script lang="ts">
  import { page } from "$app/state";
  import { goto } from "$app/navigation";
  import { Activity, Bell, Bot, BriefcaseBusiness, ClipboardList, FileText, FolderKanban, Gauge, LayoutGrid, MemoryStick, Moon, Settings2, Sun, X, Power, Rocket } from "@lucide/svelte";
  import type { Overview, SystemAlert, SystemMetric } from "$lib/api";
  import { formatDateTime, formatTime } from "$lib/format";
  import { theme } from "$lib/theme";

  export let connected = false;
  export let overview: Overview | null = null;
  export let metrics: SystemMetric[] = [];
  export let alerts: SystemAlert[] = [];
  export let onLogout: () => Promise<void>;

  let alertsOpen = false;

  const nav = [
    { label: "System Map", href: "/", icon: LayoutGrid },
    { label: "Command", href: "/command", icon: Gauge },
    { label: "Portfolio", href: "/portfolio", icon: BriefcaseBusiness },
    { label: "Blotter", href: "/blotter", icon: ClipboardList },
    { label: "Memory", href: "/memory", icon: MemoryStick },
    { label: "Config", href: "/config", icon: Settings2 },
    { label: "Gemini OAuth", href: "/gemini-oauth", icon: Bot },
    { label: "Logs", href: "/logs", icon: FolderKanban },
    { label: "Reports", href: "/reports", icon: FileText },
    { label: "Setup", href: "/setup", icon: Rocket },
  ];
</script>

<div class="hud-scanline"></div>
<div class="hud-vignette"></div>

<div class="app-shell">
  <aside class="rail">
    <div class="rail__brand">
      <Bot size={24} class="text-emerald" />
    </div>

    <nav class="flex flex-col gap-4">
      {#each nav as item}
        <button
          class:active={page.url.pathname === item.href}
          class="rail__link"
          title={item.label}
          on:click={() => goto(item.href)}
        >
          <svelte:component this={item.icon} size={20} />
        </button>
      {/each}
    </nav>

    <div class="mt-auto flex flex-col gap-4">
      <button
        class="rail__link"
        class:text-emerald={connected}
        class:text-crimson={!connected}
        title={connected ? "Uplink Active" : "Uplink Severed"}
      >
        <Activity size={20} />
      </button>

      <button
        class="rail__link text-crimson hover:bg-crimson-dim"
        title="Terminate Session"
        on:click={() => onLogout()}
      >
        <Power size={20} />
      </button>
    </div>
  </aside>

  <div class="workspace">
    <header class="command-band">
      <div class="flex items-center gap-6">
        <div class="status-metric">
          <span class="status-metric__label">MARKET STATE</span>
          <span class="status-metric__value" class:text-emerald={overview?.market.is_market_day} class:text-amber={!overview?.market.is_market_day}>
            {overview?.market.is_market_day ? "TRADING" : "HALTED"}
          </span>
        </div>

        <div class="status-metric">
          <span class="status-metric__label">LATENCY</span>
          <span class="status-metric__value mono">24ms</span>
        </div>
      </div>

      <div class="status-strip hidden md:flex">
        {#each metrics as metric}
          <div class="status-metric">
            <span class="status-metric__label">{metric.label}</span>
            <span class="status-metric__value mono" class:text-emerald={metric.tone === 'positive'} class:text-crimson={metric.tone === 'negative'} class:text-amber={metric.tone === 'warning'}>
              {metric.value}
            </span>
          </div>
        {/each}
      </div>

      <div class="flex items-center gap-4">
        <div class="status-metric text-right">
          <span class="status-metric__label">SYSTEM TIME</span>
          <span class="status-metric__value mono">
            {overview ? formatTime(overview.market.timestamp_utc) : "--:--:--"}
          </span>
        </div>

        <button
          class="rail__link"
          title={$theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          on:click={() => theme.toggle()}
        >
          {#if $theme === 'dark'}
            <Sun size={20} />
          {:else}
            <Moon size={20} />
          {/if}
        </button>

        <button
          class:text-amber={alerts.length > 0}
          class="rail__link relative"
          on:click={() => (alertsOpen = !alertsOpen)}
        >
          <Bell size={20} />
          {#if alerts.length > 0}
            <span class="absolute -top-1 -right-1 w-2 h-2 bg-amber rounded-full animate-pulse"></span>
          {/if}
        </button>
      </div>
    </header>

    <main class="main-stage">
      <slot />
    </main>
  </div>

</div>

{#if alertsOpen}
  <div class="alerts-overlay" role="presentation" on:click={() => (alertsOpen = false)}>
    <div class="alerts-panel panel flex flex-col" role="dialog" on:click|stopPropagation>
      <div class="p-4 border-b border-subtle flex justify-between items-center bg-obsidian-700">
        <div class="status-metric">
          <span class="status-metric__label">ALERT STACK</span>
          <span class="status-metric__value">{alerts.length} INCIDENTS</span>
        </div>
        <button class="rail__link" on:click={() => (alertsOpen = false)}>
          <X size={16} />
        </button>
      </div>

      <div class="alerts-body p-4 space-y-4">
        {#if alerts.length}
          {#each alerts as alert}
            <button
              class="alert-item w-full text-left p-3 border-l-2 bg-obsidian-900 cursor-pointer transition-colors border-y-0 border-r-0"
              class:border-crimson={alert.severity === 'critical'}
              class:border-amber={alert.severity === 'warning'}
              on:click={() => { alertsOpen = false; goto(alert.route); }}
            >
              <div class="flex justify-between items-start mb-1">
                <span class="status-metric__label">{alert.severity}</span>
              </div>
              <div class="font-bold text-sm mb-1">{alert.title}</div>
              <p class="text-xs text-ink-secondary">{alert.detail}</p>
            </button>
          {/each}
        {:else}
          <div class="text-center py-8 text-ink-dim text-xs uppercase tracking-widest">Zero Threats Detected</div>
        {/if}
      </div>
    </div>
  </div>
{/if}

<style>
  .flex { display: flex; }
  .flex-col { flex-direction: column; }
  .flex-1 { flex: 1 1 0%; }
  .items-center { align-items: center; }
  .items-start { align-items: flex-start; }
  .justify-between { justify-content: space-between; }
  .justify-end { justify-content: flex-end; }
  .gap-4 { gap: 1rem; }
  .gap-6 { gap: 1.5rem; }
  .mt-auto { margin-top: auto; }
  .relative { position: relative; }
  .absolute { position: absolute; }
  .fixed { position: fixed; }
  .inset-0 { top: 0; right: 0; bottom: 0; left: 0; }
  .-top-1 { top: -0.25rem; }
  .-right-1 { right: -0.25rem; }
  .text-right { text-align: right; }
  .text-center { text-align: center; }
  .text-left { text-align: left; }
  .hidden { display: none; }
  @media (min-width: 768px) { .md\:flex { display: flex; } }
  .p-4 { padding: 1rem; }
  .p-3 { padding: 0.75rem; }
  .py-8 { padding-top: 2rem; padding-bottom: 2rem; }
  .space-y-4 > * + * { margin-top: 1rem; }
  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .border-l-2 { border-left-width: 2px; }
  .border-y-0 { border-top-width: 0; border-bottom-width: 0; }
  .border-r-0 { border-right-width: 0; }
  .border-0 { border-width: 0; }
  .text-xs { font-size: 0.75rem; }
  .text-sm { font-size: 0.875rem; }
  .font-bold { font-weight: 700; }
  .mb-1 { margin-bottom: 0.25rem; }
  .w-full { width: 100%; }
  .w-80 { width: 20rem; }
  .w-2 { width: 0.5rem; }
  .h-2 { height: 0.5rem; }
  .z-\[200\] { z-index: 200; }
  .z-10 { z-index: 10; }
  .pointer-events-none { pointer-events: none; }
  .pointer-events-auto { pointer-events: auto; }
  .overflow-y-auto { overflow-y: auto; }
  .cursor-pointer { cursor: pointer; }
  .backdrop-blur-sm { backdrop-filter: blur(4px); }
  .rounded-full { border-radius: 9999px; }
  .uppercase { text-transform: uppercase; }
  .tracking-widest { letter-spacing: 0.1em; }
  .transition-colors { transition: color 0.15s, background-color 0.15s, border-color 0.15s; }
  .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }

  .alerts-overlay {
    position: fixed;
    inset: 0;
    z-index: 200;
    background: rgba(5, 6, 8, 0.6);
    backdrop-filter: blur(4px);
    display: flex;
    justify-content: flex-end;
  }

  .alerts-panel {
    width: 20rem;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .alerts-body {
    flex: 1 1 0%;
    overflow-y: auto;
  }

  .alert-item {
    display: block;
    width: 100%;
    text-align: left;
    background: var(--obsidian-900);
    border-left-width: 2px;
    border-top-width: 0;
    border-bottom-width: 0;
    border-right-width: 0;
    cursor: pointer;
    transition: background-color 0.15s;
  }

  .alert-item:hover {
    background: var(--obsidian-700);
  }
</style>
