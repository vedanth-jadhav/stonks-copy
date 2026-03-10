<script lang="ts">
  import { onDestroy, onMount } from "svelte";
  import { goto } from "$app/navigation";
  import Panel from "$components/Panel.svelte";
  import { api, type GeminiOAuthAccount, type GeminiOAuthLoginSession, type GeminiOAuthSettings } from "$lib/api";
  import { controlRoom } from "$lib/control-room";
  import { Rocket, CheckCircle, AlertTriangle, RefreshCcw, Zap, Bot, Clock, Shield, Database, Key } from "@lucide/svelte";

  // ── CLIProxy / Binary state ──────────────────────────────────────────────────
  let oauthSettings: GeminiOAuthSettings | null = null;
  let installingBinary = false;
  let binaryError = "";

  // ── Gemini OAuth account state ───────────────────────────────────────────────
  let accounts: GeminiOAuthAccount[] = [];
  let session: GeminiOAuthLoginSession | null = null;
  let loginMode: "google_one" | "code_assist" = "code_assist";
  let projectId = "";
  let startingLogin = false;
  let oauthError = "";
  let intervalId: ReturnType<typeof setInterval> | null = null;

  // ── Derived ──────────────────────────────────────────────────────────────────
  $: isCodeAssist = loginMode === "code_assist";
  $: effectiveProjectId = isCodeAssist ? projectId.trim() : "";
  $: binaryReady = oauthSettings?.binary_exists === true;
  $: accountReady = accounts.some((a) => a.status === "ready");
  $: canLaunch = binaryReady && accountReady;

  // ── Config-derived env check ─────────────────────────────────────────────────
  $: settings = $controlRoom.config?.settings as Record<string, unknown> | undefined;
  $: cliproxy = (settings?.cliproxy ?? {}) as Record<string, unknown>;
  $: exa = (settings?.exa ?? {}) as Record<string, unknown>;
  $: screener = (settings?.screener ?? {}) as Record<string, unknown>;
  $: db = (settings?.database ?? {}) as Record<string, unknown>;
  $: market = (settings?.market ?? {}) as Record<string, unknown>;

  $: envRows = [
    { label: "CLIPROXY_BASE_URL", ok: Boolean(cliproxy.base_url) },
    { label: "CLIPROXY_API_KEY", ok: Boolean(cliproxy.api_key) },
    { label: "EXA_API_KEYS", ok: Array.isArray(exa.api_keys) ? (exa.api_keys as unknown[]).length > 0 : Boolean(exa.api_keys) },
    { label: "SCREENER_BINARY_PATH", ok: Boolean(screener.binary_path) },
    { label: "DATABASE_URL", ok: Boolean(db.url) },
  ];

  $: providerHealth = $controlRoom.overview?.provider_health as Record<string, { status: string }> | undefined;

  // ── Actions ──────────────────────────────────────────────────────────────────
  async function installBinary() {
    if (!$controlRoom.csrfToken) return;
    installingBinary = true;
    binaryError = "";
    try {
      oauthSettings = await api.installGeminiOAuthCliProxy($controlRoom.csrfToken);
    } catch (err) {
      binaryError = err instanceof Error ? err.message : "Install failed.";
    } finally {
      installingBinary = false;
    }
  }

  async function launchLogin() {
    if (!$controlRoom.csrfToken) return;
    startingLogin = true;
    oauthError = "";
    try {
      session = await api.startGeminiOAuthLogin($controlRoom.csrfToken, loginMode, effectiveProjectId);
    } catch (err) {
      oauthError = err instanceof Error ? err.message : "Login failed.";
    } finally {
      startingLogin = false;
    }
  }

  async function refreshProviders() {
    await controlRoom.refreshAll();
  }

  onMount(async () => {
    const [s, a, sess] = await Promise.all([
      api.geminiOAuthSettings(),
      api.geminiOAuthAccounts(),
      api.geminiOAuthLoginSession(),
    ]);
    oauthSettings = s;
    accounts = a;
    session = sess;
    loginMode = s.default_login_mode;
    projectId = s.default_login_mode === "code_assist" ? s.default_project_id : "";

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

<div class="space-y-8">
  <!-- Page header -->
  <section class="flex justify-between items-end border-b border-subtle pb-6">
    <div class="space-y-1">
      <div class="flex items-center gap-2 text-emerald">
        <Rocket size={14} />
        <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">System Onboarding</span>
      </div>
      <h1 class="text-3xl font-bold tracking-tight">Setup <span class="text-emerald">Wizard</span></h1>
      <p class="text-ink-secondary text-sm max-w-xl">Complete each section to get the system operational on this machine.</p>
    </div>

    <div class="flex gap-4 items-center">
      <div class="status-metric text-right">
        <span class="status-metric__label">READINESS</span>
        <span class="status-metric__value mono" class:text-emerald={canLaunch} class:text-amber={!canLaunch}>
          {canLaunch ? "GO" : "NOT READY"}
        </span>
      </div>
    </div>
  </section>

  <!-- STEP 1 — Environment Variables -->
  <div class="step-block">
    <div class="step-label">
      <span class="step-num">01</span>
      <span class="step-title">Environment Variables</span>
    </div>

    <Panel eyebrow="CONFIGURATION" title="Env Var Status" tone="emerald">
      <div class="space-y-4">
        <p class="text-ink-secondary text-xs leading-relaxed">
          Copy <code class="mono text-emerald">.env.example</code> to <code class="mono text-emerald">.env</code> and fill in the values below. The app reads from environment variables — editing <code class="mono text-emerald">.env</code> and restarting the service picks them up.
        </p>

        <div class="grid grid-cols-1 gap-2">
          {#each envRows as row}
            <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
              <span class="mono text-[10px] text-ink-dim uppercase tracking-wider">{row.label}</span>
              <span class="mono text-[10px] font-bold" class:text-emerald={row.ok} class:text-amber={!row.ok}>
                {row.ok ? "CONFIGURED" : "MISSING"}
              </span>
            </div>
          {/each}
        </div>

        <details class="border border-subtle">
          <summary class="p-3 cursor-pointer mono text-[10px] text-ink-dim uppercase tracking-widest hover:text-emerald transition-colors select-none">.env.example — expand to copy</summary>
          <pre class="p-4 bg-obsidian-900 text-[10px] mono text-emerald overflow-x-auto leading-relaxed whitespace-pre">CLIPROXY_BASE_URL=http://127.0.0.1:8317
CLIPROXY_API_KEY=
CLIPROXY_TIMEOUT_SECONDS=30
GEMINI_BOSS_MODEL=gemini-3.1-pro-preview
GEMINI_AGENTS_MODEL=gemini-3-flash-preview
GEMINI_REFLECTION_MODEL=gemini-3-flash-preview

EXA_API_KEYS=
EXA_TIMEOUT_SECONDS=20
EXA_DAILY_BUDGET_PER_AGENT=20

SCREENER_BINARY_PATH=../screener/screener
SCREENER_TIMEOUT_SECONDS=30
SCREENER_RETRIES=2

DATABASE_URL=sqlite:///data/quant_trading.db
INITIAL_CAPITAL=1000000

WEB_HOST=127.0.0.1
WEB_PORT=8800
WEB_LOG_LEVEL=warning
WEB_PASSWORD=quant
WEB_SESSION_SECRET=change-me
WEB_WEBSOCKET_REFRESH_SECONDS=5</pre>
        </details>
      </div>
    </Panel>
  </div>

  <!-- STEP 2 — Provider Health -->
  <div class="step-block">
    <div class="step-label">
      <span class="step-num">02</span>
      <span class="step-title">Provider Health</span>
    </div>

    <Panel eyebrow="DIAGNOSTICS" title="System Providers" tone="emerald">
      <div class="space-y-4">
        {#if providerHealth}
          <div class="grid grid-cols-1 gap-2">
            {#each Object.entries(providerHealth) as [name, data]}
              {@const isReady = data.status === "READY" || data.status === "OK"}
              <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
                <span class="mono text-[10px] text-ink-dim uppercase tracking-wider">{name}</span>
                <span class="mono text-[10px] font-bold" class:text-emerald={isReady} class:text-amber={!isReady}>
                  {data.status ?? "UNKNOWN"}
                </span>
              </div>
            {/each}
          </div>
        {:else}
          <div class="flex items-center gap-2 text-ink-dim text-xs">
            <Zap size={14} class="animate-pulse" />
            <span class="mono uppercase tracking-widest">Loading health data...</span>
          </div>
        {/if}

        <button
          class="flex items-center gap-2 px-4 py-2 border border-subtle text-ink-dim mono text-[10px] font-bold uppercase tracking-widest hover:text-emerald hover:border-emerald transition-all"
          on:click={refreshProviders}
        >
          <RefreshCcw size={12} />
          REFRESH
        </button>
      </div>
    </Panel>
  </div>

  <!-- STEP 3 — CLIProxy Binary -->
  <div class="step-block">
    <div class="step-label">
      <span class="step-num">03</span>
      <span class="step-title">CLIProxy Binary</span>
    </div>

    <Panel eyebrow="BINARY" title="CLIProxy Launcher" tone={binaryReady ? "emerald" : "amber"}>
      <div class="space-y-4">
        <p class="text-ink-secondary text-xs leading-relaxed">
          The CLIProxy binary bridges the Gemini OAuth accounts to the local OpenAI-compatible API. It must be installed before adding accounts.
        </p>

        <div class="grid grid-cols-1 gap-2">
          <div class="flex justify-between p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">INSTALLED VERSION</span>
            <span class="mono text-[10px] font-bold" class:text-emerald={Boolean(oauthSettings?.installed_version)} class:text-ink-dim={!oauthSettings?.installed_version}>
              {oauthSettings?.installed_version ?? "--"}
            </span>
          </div>
          <div class="flex justify-between p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">RUNTIME STATUS</span>
            <span class="mono text-[10px] font-bold" class:text-emerald={oauthSettings?.runtime_status === "running"} class:text-ink-dim={oauthSettings?.runtime_status !== "running"}>
              {oauthSettings?.runtime_status ?? "--"}
            </span>
          </div>
          <div class="flex justify-between p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">BINARY EXISTS</span>
            <span class="mono text-[10px] font-bold" class:text-emerald={binaryReady} class:text-amber={!binaryReady}>
              {binaryReady ? "YES" : "NO"}
            </span>
          </div>
        </div>

        {#if binaryError}
          <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson mono text-[10px] uppercase tracking-widest flex items-center gap-2">
            <AlertTriangle size={12} />
            {binaryError}
          </div>
        {/if}

        <button
          class="w-full py-2 bg-emerald text-obsidian-900 mono text-[10px] font-bold uppercase tracking-widest hover:bg-emerald-glow transition-all disabled:opacity-30"
          disabled={installingBinary}
          on:click={installBinary}
        >
          {installingBinary ? "INSTALLING..." : binaryReady ? "REINSTALL" : "INSTALL CLIPROXY"}
        </button>
      </div>
    </Panel>
  </div>

  <!-- STEP 4 — Gemini OAuth Accounts -->
  <div class="step-block">
    <div class="step-label">
      <span class="step-num">04</span>
      <span class="step-title">Gemini OAuth Accounts</span>
    </div>

    <Panel eyebrow="CREDENTIALS" title="Gemini Account Pool" tone={accountReady ? "emerald" : "amber"}>
      <div class="space-y-4">
        <p class="text-ink-secondary text-xs leading-relaxed">
          Add at least one Google account to provide Gemini quota. You'll be redirected to a browser window to complete the OAuth handoff.
        </p>

        <!-- Existing accounts -->
        {#if accounts.length > 0}
          <div class="grid grid-cols-1 gap-2">
            {#each accounts as account}
              <div class="flex justify-between items-center p-3 bg-obsidian-900 border border-subtle">
                <span class="mono text-[10px] text-ink-secondary">{account.email}</span>
                <span
                  class="mono text-[10px] font-bold"
                  class:text-emerald={account.status === "ready"}
                  class:text-amber={account.status === "exhausted"}
                  class:text-crimson={account.status === "auth-error"}
                >
                  {account.status.toUpperCase()}
                </span>
              </div>
            {/each}
          </div>
        {:else}
          <div class="flex items-center gap-2 p-3 bg-obsidian-900 border border-subtle text-ink-dim">
            <Bot size={14} />
            <span class="mono text-[10px] uppercase tracking-widest">No accounts in cluster</span>
          </div>
        {/if}

        <!-- Session status indicator -->
        {#if session && session.status === "running"}
          <div class="flex items-center gap-3 p-3 bg-obsidian-900 border border-amber/30">
            <div class="w-2 h-2 rounded-full bg-amber animate-pulse"></div>
            <span class="mono text-[10px] font-bold text-amber">BROWSER_AUTH_PENDING — complete sign-in in the browser window</span>
          </div>
        {:else if session?.status === "completed"}
          <div class="flex items-center gap-2 p-2 text-emerald">
            <CheckCircle size={14} />
            <span class="mono text-[10px]">Account added successfully.</span>
          </div>
        {/if}

        <!-- Add account form -->
        <div class="space-y-3 border-t border-subtle pt-4">
          <div class="space-y-1">
            <label class="status-metric__label" for="setup-login-mode">AUTH_PROTOCOL</label>
            <select
              id="setup-login-mode"
              class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald"
              bind:value={loginMode}
            >
              <option value="google_one">GOOGLE_ONE (CONSUMER)</option>
              <option value="code_assist">CODE_ASSIST (CLOUD_PROJECT)</option>
            </select>
          </div>

          {#if isCodeAssist}
            <div class="space-y-1">
              <label class="status-metric__label" for="setup-project-id">GCP_PROJECT_ID</label>
              <input
                id="setup-project-id"
                class="w-full bg-obsidian-900 border border-subtle p-2 mono text-[10px] text-emerald outline-none focus:border-emerald"
                bind:value={projectId}
                placeholder="e.g. keen-virtue-484413"
              />
            </div>
          {/if}

          {#if oauthError}
            <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson mono text-[10px] uppercase tracking-widest flex items-center gap-2">
              <AlertTriangle size={12} />
              {oauthError}
            </div>
          {/if}

          <button
            class="w-full py-3 bg-amber-dim border border-amber text-amber mono text-[10px] font-bold uppercase tracking-widest hover:bg-amber/20 transition-all disabled:opacity-30"
            disabled={!binaryReady || startingLogin || session?.status === "running" || (isCodeAssist && !effectiveProjectId)}
            on:click={launchLogin}
          >
            {session?.status === "running" ? "BROWSER_AUTH_PENDING..." : startingLogin ? "LAUNCHING..." : "ADD ACCOUNT"}
          </button>

          {#if !binaryReady}
            <p class="mono text-[9px] text-amber uppercase tracking-widest">Install the CLIProxy binary in Step 03 first.</p>
          {/if}
        </div>
      </div>
    </Panel>
  </div>

  <!-- STEP 5 — Market Timing -->
  <div class="step-block">
    <div class="step-label">
      <span class="step-num">05</span>
      <span class="step-title">Market Timing</span>
    </div>

    <Panel eyebrow="SCHEDULE" title="Market Windows" tone="emerald">
      <div class="space-y-4">
        <p class="text-ink-secondary text-xs leading-relaxed">
          These values are set via environment variables and read at startup. To change them, update <code class="mono text-emerald">.env</code> and restart the service.
        </p>

        <div class="grid grid-cols-1 gap-2">
          <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">TIMEZONE</span>
            <span class="mono text-[10px] font-bold text-emerald">{String(market.timezone ?? "Asia/Kolkata")}</span>
          </div>
          <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">ENTRY WINDOW OPEN</span>
            <span class="mono text-[10px] font-bold text-emerald">{String(market.entry_window_open ?? "09:30")}</span>
          </div>
          <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">ENTRY WINDOW CLOSE</span>
            <span class="mono text-[10px] font-bold text-emerald">{String(market.entry_window_close ?? "15:00")}</span>
          </div>
          <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">EXIT WINDOW CLOSE</span>
            <span class="mono text-[10px] font-bold text-emerald">{String(market.exit_window_close ?? "15:25")}</span>
          </div>
          <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">INITIAL CAPITAL</span>
            <span class="mono text-[10px] font-bold text-emerald">₹{Number(market.initial_capital ?? 1000000).toLocaleString("en-IN")}</span>
          </div>
          <div class="flex justify-between items-center p-2 bg-obsidian-900 border border-subtle">
            <span class="status-metric__label">BENCHMARK</span>
            <span class="mono text-[10px] font-bold text-emerald">{String(market.benchmark ?? "^NSEI")}</span>
          </div>
        </div>
      </div>
    </Panel>
  </div>

  <!-- Launch footer -->
  <div class="border-t border-subtle pt-6 flex flex-col items-end gap-3">
    {#if !canLaunch}
      <div class="flex items-center gap-2 text-amber mono text-[10px] uppercase tracking-widest">
        <AlertTriangle size={14} />
        {#if !binaryReady && !accountReady}
          Install CLIProxy binary and add a Gemini account to proceed.
        {:else if !binaryReady}
          Install the CLIProxy binary (Step 03) to proceed.
        {:else}
          Add at least one Gemini account (Step 04) to proceed.
        {/if}
      </div>
    {/if}

    <button
      class="flex items-center gap-3 px-8 py-4 bg-emerald text-obsidian-900 mono text-[11px] font-bold uppercase tracking-[0.3em] hover:bg-emerald-glow transition-all disabled:opacity-30 disabled:cursor-not-allowed"
      disabled={!canLaunch}
      on:click={() => goto("/")}
    >
      <Rocket size={16} />
      LAUNCH SYSTEM
    </button>
  </div>
</div>

<style>
  .space-y-8 > * + * { margin-top: 2rem; }
  .space-y-4 > * + * { margin-top: 1rem; }
  .space-y-3 > * + * { margin-top: 0.75rem; }
  .space-y-1 > * + * { margin-top: 0.25rem; }

  .grid { display: grid; }
  .grid-cols-1 { grid-template-columns: repeat(1, minmax(0, 1fr)); }

  .flex { display: flex; }
  .flex-col { flex-direction: column; }
  .items-center { align-items: center; }
  .items-end { align-items: flex-end; }
  .justify-between { justify-content: space-between; }

  .gap-2 { gap: 0.5rem; }
  .gap-3 { gap: 0.75rem; }
  .gap-4 { gap: 1rem; }

  .border-b { border-bottom: 1px solid var(--border-subtle); }
  .border-t { border-top: 1px solid var(--border-subtle); }
  .border-subtle { border-color: var(--border-subtle); }
  .pb-6 { padding-bottom: 1.5rem; }
  .pt-4 { padding-top: 1rem; }
  .pt-6 { padding-top: 1.5rem; }
  .p-2 { padding: 0.5rem; }
  .p-3 { padding: 0.75rem; }
  .p-4 { padding: 1rem; }
  .px-4 { padding-left: 1rem; padding-right: 1rem; }
  .px-8 { padding-left: 2rem; padding-right: 2rem; }
  .py-2 { padding-top: 0.5rem; padding-bottom: 0.5rem; }
  .py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
  .py-4 { padding-top: 1rem; padding-bottom: 1rem; }

  .text-right { text-align: right; }
  .text-xs { font-size: 0.75rem; }
  .font-bold { font-weight: 700; }
  .leading-relaxed { line-height: 1.625; }
  .tracking-widest { letter-spacing: 0.1em; }
  .uppercase { text-transform: uppercase; }

  .w-full { width: 100%; }
  .w-2 { width: 0.5rem; }
  .h-2 { height: 0.5rem; }
  .max-w-xl { max-width: 36rem; }
  .rounded-full { border-radius: 9999px; }
  .overflow-x-auto { overflow-x: auto; }
  .select-none { user-select: none; }

  .transition-all { transition: all 0.15s ease; }
  .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

  .disabled\:opacity-30:disabled { opacity: 0.3; }

  /* Step layout */
  .step-block {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .step-label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .step-num {
    font-family: var(--font-mono, monospace);
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    color: var(--emerald);
    opacity: 0.6;
  }

  .step-title {
    font-family: var(--font-mono, monospace);
    font-size: 0.625rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-secondary, #9ca3af);
  }

  code {
    font-family: var(--font-mono, monospace);
  }

  pre {
    white-space: pre;
  }

  details > summary {
    list-style: none;
  }

  details > summary::-webkit-details-marker {
    display: none;
  }
</style>
