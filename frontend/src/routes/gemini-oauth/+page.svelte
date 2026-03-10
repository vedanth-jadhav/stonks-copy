<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import Panel from "$components/Panel.svelte";
  import { api, type GeminiOAuthAccount, type GeminiOAuthLoginSession, type GeminiOAuthSettings } from "$lib/api";
  import { controlRoom } from "$lib/control-room";
  import { formatDateTime, formatTime } from "$lib/format";
  import { Bot, UserCheck, Zap, RefreshCcw, Trash2, Shield, Settings2, ExternalLink, Cpu, HardDrive, AlertTriangle } from "@lucide/svelte";

  const statusCopy: Record<string, string> = {
    ready: "READY",
    warning: "WARNING",
    exhausted: "EXHAUSTED",
    unknown: "UNKNOWN",
    "auth-error": "AUTH_ERROR",
  };

  const sessionCopy: Record<string, string> = {
    idle: "IDLE",
    running: "ACTIVE_HANDOFF",
    completed: "COMPLETED",
    failed: "FAILED",
    timed_out: "TIMED_OUT",
  };

  let settings: GeminiOAuthSettings | null = null;
  let accounts: GeminiOAuthAccount[] = [];
  let session: GeminiOAuthLoginSession | null = null;
  let binaryPath = "";
  let loginMode: "google_one" | "code_assist" = "code_assist";
  let projectId = "";
  let pageError = "";
  let savingSettings = false;
  let installingBinary = false;
  let startingLogin = false;
  let busyAccountId = "";
  let intervalId: ReturnType<typeof setInterval> | null = null;
  let savedCodeAssistProjectId = "";

  $: isCodeAssist = loginMode === "code_assist";
  $: effectiveProjectId = isCodeAssist ? projectId.trim() : "";

  function usageLabel(percent: number | null) {
    if (percent === null) return "Unknown";
    return `${Math.round(percent)}% REMAINING`;
  }

  async function loadPage() {
    const [settingsPayload, accountsPayload, sessionPayload] = await Promise.all([
      api.geminiOAuthSettings(),
      api.geminiOAuthAccounts(),
      api.geminiOAuthLoginSession(),
    ]);
    settings = settingsPayload;
    accounts = accountsPayload;
    session = sessionPayload;
    binaryPath = settingsPayload.binary_path;
    loginMode = settingsPayload.default_login_mode;
    projectId = settingsPayload.default_login_mode === "code_assist" ? settingsPayload.default_project_id : "";
    savedCodeAssistProjectId = settingsPayload.default_project_id;
  }

  async function saveSettings() {
    if (!$controlRoom.csrfToken) return;
    savingSettings = true;
    pageError = "";
    try {
      settings = await api.updateGeminiOAuthSettings($controlRoom.csrfToken, binaryPath, loginMode, effectiveProjectId);
      binaryPath = settings.binary_path;
      loginMode = settings.default_login_mode;
      savedCodeAssistProjectId = settings.default_project_id;
      projectId = settings.default_login_mode === "code_assist" ? settings.default_project_id : "";
    } catch (error) {
      pageError = error instanceof Error ? error.message : "Failed to save settings.";
    } finally {
      savingSettings = false;
    }
  }

  async function installCliProxy() {
    if (!$controlRoom.csrfToken) return;
    installingBinary = true;
    pageError = "";
    try {
      settings = await api.installGeminiOAuthCliProxy($controlRoom.csrfToken);
      binaryPath = settings.binary_path;
    } catch (error) {
      pageError = error instanceof Error ? error.message : "Failed to install CLIProxy.";
    } finally {
      installingBinary = false;
    }
  }

  async function launchLogin() {
    if (!$controlRoom.csrfToken) return;
    startingLogin = true;
    pageError = "";
    try {
      session = await api.startGeminiOAuthLogin($controlRoom.csrfToken, loginMode, effectiveProjectId);
    } catch (error) {
      pageError = error instanceof Error ? error.message : "Failed to start login.";
    } finally {
      startingLogin = false;
    }
  }

  async function refreshUsage(accountId: string) {
    if (!$controlRoom.csrfToken) return;
    busyAccountId = accountId;
    try {
      const updated = await api.refreshGeminiOAuthUsage($controlRoom.csrfToken, accountId);
      accounts = [updated, ...accounts.filter((account) => account.account_id !== updated.account_id)];
    } finally {
      busyAccountId = "";
    }
  }

  async function removeAccount(accountId: string) {
    if (!$controlRoom.csrfToken) return;
    busyAccountId = accountId;
    try {
      await api.deleteGeminiOAuthAccount($controlRoom.csrfToken, accountId);
      accounts = accounts.filter((account) => account.account_id !== accountId);
    } finally {
      busyAccountId = "";
    }
  }

  onMount(async () => {
    await loadPage();
    intervalId = setInterval(async () => {
      if (!session || session.status !== "running") return;
      session = await api.geminiOAuthLoginSession();
      if (session.status === "completed") {
        accounts = await api.geminiOAuthAccounts();
      }
    }, 1000);
  });

  onDestroy(() => {
    if (intervalId) clearInterval(intervalId);
  });
</script>

<div class="space-y-6">
  <section class="flex justify-between items-end border-b border-subtle pb-6">
    <div class="space-y-1">
      <div class="flex items-center gap-2 text-emerald">
        <Bot size={14} />
        <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Model Quota Orchestration</span>
      </div>
      <h1 class="text-3xl font-bold tracking-tight">Gemini <span class="text-emerald">Pool</span></h1>
      <p class="text-ink-secondary text-sm max-w-xl">Multi-account OAuth management, CLIProxy readiness, and model headroom monitoring.</p>
    </div>

    <div class="flex gap-4">
      <div class="status-metric text-right">
        <span class="status-metric__label">TOTAL ACCOUNTS</span>
        <span class="status-metric__value mono text-emerald">{accounts.length}</span>
      </div>
      <div class="status-metric text-right">
        <span class="status-metric__label">READY</span>
        <span class="status-metric__value mono text-emerald">{accounts.filter(a => a.status === 'ready').length}</span>
      </div>
    </div>
  </section>

  <div class="grid grid-cols-1 lg:grid-cols-[400px,1fr] gap-6 items-start">
    <div class="space-y-6">
      <Panel eyebrow="BINARY" title="CLIProxy Launcher" tone="emerald">
        <div class="space-y-6">
          <div class="grid grid-cols-1 gap-2">
            <div class="flex justify-between p-2 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">INSTALL</span>
              <span class="mono text-[10px] font-bold text-emerald">{settings?.installed_version || "--"}</span>
            </div>
            <div class="flex justify-between p-2 bg-obsidian-900 border border-subtle">
              <span class="status-metric__label">STATUS</span>
              <span class="mono text-[10px] font-bold text-emerald">{settings?.runtime_status || "--"}</span>
            </div>
          </div>

          <div class="space-y-2">
            <label class="status-metric__label" for="cliproxy-binary">BINARY_PATH_OVERRIDE</label>
            <input id="cliproxy-binary" class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald" bind:value={binaryPath} />
          </div>

          <div class="flex gap-2">
            <button class="flex-1 py-2 bg-emerald text-obsidian-900 mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all" disabled={savingSettings} on:click={saveSettings}>
              {savingSettings ? "SAVING..." : "UPDATE"}
            </button>
            <button class="flex-1 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-emerald hover:border-emerald transition-all" disabled={installingBinary || session?.status === "running"} on:click={installCliProxy}>
              {installingBinary ? "INSTALLING..." : "REINSTALL"}
            </button>
          </div>
        </div>
      </Panel>

      <Panel eyebrow="OAUTH HANDOFF" title="Live Session" tone="amber">
        <div class="space-y-6">
          <div class="flex items-center gap-3 p-3 bg-obsidian-900 border border-amber/30">
            <div class="w-2 h-2 rounded-full animate-pulse" class:bg-amber={session?.status === 'running'} class:bg-emerald={session?.status === 'completed'} class:bg-ink-dim={!session || session.status === 'idle'}></div>
            <span class="mono text-[10px] font-bold text-amber">{session ? sessionCopy[session.status] : "IDLE"}</span>
          </div>

          <p class="text-[10px] text-ink-secondary leading-relaxed uppercase tracking-tighter opacity-80">{session?.message ?? "Awaiting initiation of Gemini OAuth login sequence."}</p>

          <div class="space-y-4 border-t border-subtle pt-4">
            <div class="space-y-2">
              <label class="status-metric__label" for="gemini-login-mode">AUTH_PROTOCOL</label>
              <select id="gemini-login-mode" class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald" bind:value={loginMode}>
                <option value="google_one">GOOGLE_ONE (CONSUMER)</option>
                <option value="code_assist">CODE_ASSIST (CLOUD_PROJECT)</option>
              </select>
            </div>

            {#if isCodeAssist}
              <div class="space-y-2">
                <label class="status-metric__label" for="gemini-project-id">GCP_PROJECT_ID</label>
                <input id="gemini-project-id" class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald" bind:value={projectId} placeholder="e.g. keen-virtue-484413" />
              </div>
            {/if}

            <button
              class="w-full py-3 bg-amber-dim border border-amber text-amber mono text-[10px] font-bold uppercase tracking-widest hover:bg-amber/20 transition-all disabled:opacity-30"
              disabled={!settings?.binary_exists || startingLogin || session?.status === "running" || (isCodeAssist && !effectiveProjectId)}
              on:click={launchLogin}
            >
              {session?.status === "running" ? "BROWSWER_AUTH_PENDING..." : startingLogin ? "LAUNCHING..." : "ADD_ACCOUNT"}
            </button>
          </div>
        </div>
      </Panel>
    </div>

    <Panel eyebrow="ACCOUNT CLUSTER" title="Gemini Quota Board" tone="emerald">
      <div class="space-y-6">
        {#each accounts as account}
          <div class="p-6 bg-obsidian-800 border border-subtle relative group hover:border-emerald transition-all">
            <div class="flex justify-between items-start mb-6">
              <div class="space-y-1">
                <div class="flex items-center gap-2">
                  <UserCheck size={16} class="text-emerald" />
                  <span class="mono text-sm font-bold">{account.email}</span>
                </div>
                <div class="mono text-[9px] text-ink-dim uppercase tracking-widest">
                  {account.project_id ? `PROJECT: ${account.project_id}` : "NO_PROJECT_LINK"}
                </div>
              </div>

              <div class="flex flex-col text-right gap-1">
                <span class="mono text-[10px] font-bold" class:text-emerald={account.status === 'ready'} class:text-amber={account.status === 'exhausted'} class:text-crimson={account.status === 'auth-error'}>
                  {statusCopy[account.status] ?? account.status}
                </span>
                <span class="text-[9px] text-ink-dim uppercase mono">{formatTime(account.modified_at)}</span>
              </div>
            </div>

            <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {#each account.usage.models as model}
                <div class="p-3 bg-obsidian-900 border border-subtle space-y-2">
                  <span class="status-metric__label text-[9px] truncate block">{model.model_id}</span>
                  <div class="mono text-xs font-bold" class:text-emerald={model.available} class:text-amber={!model.available}>
                    {usageLabel(model.remaining_percent)}
                  </div>
                  <div class="h-1 bg-obsidian-700 w-full rounded-full overflow-hidden">
                    <div class="h-full bg-emerald" style="width: {model.remaining_percent ?? 0}%"></div>
                  </div>
                </div>
              {/each}
            </div>

            {#if account.usage.error}
              <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] mono uppercase tracking-widest mb-4">
                {account.usage.error}
              </div>
            {/if}

            <div class="flex justify-end gap-3 pt-4 border-t border-subtle">
              <button
                class="flex items-center gap-2 px-4 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-emerald hover:border-emerald transition-all"
                disabled={busyAccountId === account.account_id}
                on:click={() => refreshUsage(account.account_id)}
              >
                <RefreshCcw size={12} class={busyAccountId === account.account_id ? 'animate-spin' : ''} />
                REFRESH_QUOTA
              </button>
              <button
                class="flex items-center gap-2 px-4 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-crimson hover:border-crimson transition-all"
                disabled={busyAccountId === account.account_id}
                on:click={() => removeAccount(account.account_id)}
              >
                <Trash2 size={12} />
                PURGE
              </button>
            </div>
          </div>
        {/each}
        {#if !accounts.length}
           <div class="flex flex-col items-center justify-center py-40 text-ink-dim gap-4 border border-dashed border-subtle">
            <Cpu size={32} strokeWidth={1} />
            <span class="mono text-[10px] uppercase tracking-[0.3em]">No compute nodes in cluster</span>
          </div>
        {/if}
      </div>
    </Panel>
  </div>

  {#if pageError}
    <div class="p-4 bg-crimson-dim border border-crimson text-crimson mono text-xs uppercase tracking-widest flex items-center gap-3">
       <AlertTriangle size={16} />
       {pageError}
    </div>
  {/if}
</div>

<style>
  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }
  .grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }

  .space-y-1 > * + * { margin-top: 0.25rem; }
  .space-y-2 > * + * { margin-top: 0.5rem; }
  .space-y-4 > * + * { margin-top: 1rem; }
  .space-y-6 > * + * { margin-top: 1.5rem; }

  .flex { display: flex; }
  .flex-col { flex-direction: column; }
  .flex-1 { flex: 1 1 0%; }
  .items-center { align-items: center; }
  .items-end { align-items: flex-end; }
  .justify-center { justify-content: center; }
  .justify-between { justify-content: space-between; }
  .justify-end { justify-content: flex-end; }

  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .border-t { border-top: 1px solid var(--border-subtle); }
  .border-dashed { border-style: dashed; }
  .pb-6 { padding-bottom: 1.5rem; }
  .pt-4 { padding-top: 1rem; }
  .p-2 { padding: 0.5rem; }
  .p-3 { padding: 0.75rem; }
  .p-6 { padding: 1.5rem; }
  .py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
  .py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
  .py-40 { padding-top: 10rem; padding-bottom: 10rem; }

  .max-w-xl { max-width: 36rem; }
  .truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
</style>
