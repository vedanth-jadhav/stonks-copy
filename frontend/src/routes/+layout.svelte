<script lang="ts">
  import { onMount } from "svelte";
  import "$lib/../app.css";
  import LoginGate from "$components/LoginGate.svelte";
  import Shell from "$components/Shell.svelte";
  import { controlRoom } from "$lib/control-room";
  import { theme } from "$lib/theme";
  import { Zap } from "@lucide/svelte";

  onMount(() => {
    theme.init();
    void controlRoom.init();
    return () => controlRoom.destroy();
  });
</script>

<svelte:head>
  <title>Quant Control Room // HUD</title>
  <!-- svelte-ignore non-reactive-update -->
  <script>
    (function () {
      var t = localStorage.getItem('stonks-theme');
      if (t === 'light') document.documentElement.setAttribute('data-theme', 'light');
    })();
  </script>
</svelte:head>

{#if $controlRoom.booting && !$controlRoom.authenticated}
  <div class="flex flex-col items-center justify-center min-h-screen bg-obsidian-900 gap-4">
    <Zap size={32} class="text-emerald animate-pulse" />
    <div class="mono text-[10px] tracking-[0.4em] text-emerald opacity-50 uppercase">Securing Local Execution Node...</div>
  </div>
{:else if !$controlRoom.authenticated}
  <LoginGate error={$controlRoom.error} busy={$controlRoom.booting} onSubmit={(password) => controlRoom.login(password)} />
{:else}
  <Shell
    connected={$controlRoom.connected}
    overview={$controlRoom.overview}
    metrics={$controlRoom.systemMap?.top_metrics ?? []}
    alerts={$controlRoom.systemMap?.alerts ?? []}
    onLogout={() => controlRoom.logout()}
  >
    <slot />
  </Shell>
{/if}
