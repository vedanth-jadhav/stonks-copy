<script lang="ts">
  import { ShieldCheck, Zap, Lock } from "@lucide/svelte";

  export let error = "";
  export let busy = false;
  export let onSubmit: (password: string) => Promise<void>;

  let password = "quant";
</script>

<div class="hud-scanline"></div>
<div class="hud-vignette"></div>

<div class="login-gate">
  <div class="absolute top-10 left-10 flex items-center gap-2 text-emerald opacity-50">
    <Zap size={14} />
    <span class="mono text-[10px] tracking-[0.2em] uppercase font-bold">Uplink: Protected</span>
  </div>

  <form
    class="login-card panel"
    on:submit|preventDefault={async () => {
      await onSubmit(password);
    }}
  >
    <div class="space-y-6 relative z-10">
      <div class="flex justify-center">
        <div class="w-12 h-12 rounded-full border border-emerald flex items-center justify-center text-emerald animate-pulse bg-emerald-dim">
          <ShieldCheck size={24} />
        </div>
      </div>

      <div class="text-center space-y-2">
        <div class="mono text-[10px] tracking-[0.3em] text-emerald uppercase font-bold">Terminal Authorization</div>
        <h1 class="text-2xl font-bold tracking-tight">Access Control Room</h1>
        <p class="text-ink-secondary text-xs max-w-[280px] mx-auto leading-relaxed">
          Proprietary trading surface. Unauthorized access is strictly prohibited.
        </p>
      </div>

      <div class="space-y-4">
        <div class="space-y-2">
          <label class="status-metric__label" for="password">OPERATOR KEY</label>
          <div class="relative">
            <input
              id="password"
              bind:value={password}
              class="w-full bg-obsidian-900 border border-subtle p-3 pl-10 mono text-sm text-emerald focus:border-emerald outline-none transition-all"
              type="password"
              placeholder="••••••••"
            />
            <Lock size={14} class="absolute left-3 top-1/2 -translate-y-1/2 text-ink-dim" />
          </div>
        </div>

        <button
          class="w-full py-3 bg-emerald text-obsidian-900 mono text-xs font-bold uppercase tracking-[0.2em] hover:bg-emerald-glow transition-all disabled:opacity-50"
          type="submit"
          disabled={busy}
        >
          {busy ? "AUTHORIZING..." : "INITIATE UPLINK"}
        </button>
      </div>

      {#if error}
        <div class="p-3 bg-crimson-dim border border-crimson/30 text-crimson text-[10px] text-center mono uppercase tracking-widest">
          {error}
        </div>
      {/if}
    </div>

    <!-- HUD Elements -->
    <div class="absolute inset-0 pointer-events-none opacity-20">
      <div class="absolute top-0 left-0 w-20 h-px bg-emerald"></div>
      <div class="absolute top-0 left-0 h-20 w-px bg-emerald"></div>
      <div class="absolute bottom-0 right-0 w-20 h-px bg-emerald"></div>
      <div class="absolute bottom-0 right-0 h-20 w-px bg-emerald"></div>
    </div>
  </form>

  <div class="absolute bottom-10 mono text-[8px] text-ink-dim uppercase tracking-[0.4em]">
    Secure Desk // NSE Execution Node 042
  </div>
</div>

<style>
  .login-gate {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: var(--obsidian-900);
    padding: 20px;
    position: relative;
    overflow: hidden;
  }

  .login-card {
    width: 100%;
    max-width: 400px;
    padding: 40px;
    background: var(--obsidian-800);
    position: relative;
    border: 1px solid var(--border-subtle);
  }

  .flex { display: flex; }
  .items-center { align-items: center; }
  .justify-center { justify-content: center; }
  .gap-2 { gap: 0.5rem; }
  .space-y-2 > * + * { margin-top: 0.5rem; }
  .space-y-4 > * + * { margin-top: 1rem; }
  .space-y-6 > * + * { margin-top: 1.5rem; }
  .text-center { text-align: center; }
  .mx-auto { margin-left: auto; margin-right: auto; }
  .relative { position: relative; }
  .absolute { position: absolute; }
  .top-10 { top: 2.5rem; }
  .left-10 { left: 2.5rem; }
  .bottom-10 { bottom: 2.5rem; }
  .z-10 { z-index: 10; }
  .w-12 { width: 3rem; }
  .h-12 { height: 3rem; }
  .w-20 { width: 5rem; }
  .h-20 { height: 5rem; }
  .rounded-full { border-radius: 9999px; }
  .text-2xl { font-size: 1.5rem; }
  .font-bold { font-weight: 700; }
  .tracking-tight { letter-spacing: -0.025em; }
  .leading-relaxed { line-height: 1.625; }
  .opacity-50 { opacity: 0.5; }
  .opacity-20 { opacity: 0.2; }
  .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
</style>
