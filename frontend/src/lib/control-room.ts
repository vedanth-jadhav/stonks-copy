import { api, type AgentDetail, type AgentIndexRow, type ConfigPayload, type MemoryIndex, type Overview, type PortfolioPayload, type SessionState, type SystemMapPayload } from "$lib/api";
import { writable } from "svelte/store";

type ControlRoomState = {
  booting: boolean;
  connected: boolean;
  error: string;
  authenticated: boolean;
  csrfToken: string;
  session: SessionState | null;
  overview: Overview | null;
  systemMap: SystemMapPayload | null;
  runs: Array<Record<string, unknown>>;
  agents: AgentIndexRow[];
  selectedAgent: AgentDetail | null;
  portfolio: PortfolioPayload | null;
  memory: MemoryIndex | null;
  config: ConfigPayload | null;
};

type LiveSnapshotPayload = {
  overview: Overview;
  system_map: SystemMapPayload;
  runs: Array<Record<string, unknown>>;
  agents: AgentIndexRow[];
  portfolio: PortfolioPayload;
  memory: MemoryIndex;
  config: ConfigPayload;
};

const initialState: ControlRoomState = {
  booting: true,
  connected: false,
  error: "",
  authenticated: false,
  csrfToken: "",
  session: null,
  overview: null,
  systemMap: null,
  runs: [],
  agents: [],
  selectedAgent: null,
  portfolio: null,
  memory: null,
  config: null,
};

function createControlRoom() {
  const store = writable<ControlRoomState>(initialState);
  let refreshHandle: ReturnType<typeof setInterval> | null = null;
  let socket: WebSocket | null = null;
  let initialized = false;

  const updateState = (recipe: (current: ControlRoomState) => ControlRoomState) => store.update(recipe);

  async function hydrateCore() {
    const [overview, systemMap, runs, agents, portfolio, memory, config] = await Promise.all([
      api.overview(),
      api.systemMap(),
      api.runs(),
      api.agents(),
      api.portfolio(),
      api.memory(),
      api.config(),
    ]);

    let selectedAgent: AgentDetail | null = null;
    const preferred = systemMap.nodes.find((node) => node.id === "agent_06_macro") ?? systemMap.nodes[0];
    if (preferred) {
      selectedAgent = await api.agentDetail(preferred.id);
    }

    updateState((current) => ({
      ...current,
      overview,
      systemMap,
      runs,
      agents,
      portfolio,
      memory,
      config,
      selectedAgent,
      error: "",
    }));
  }

  async function refreshShell() {
    const [overview, systemMap] = await Promise.all([api.overview(), api.systemMap()]);
    updateState((current) => ({ ...current, overview, systemMap }));
  }

  function connectSocket() {
    if (typeof window === "undefined" || socket) return;
    socket = new WebSocket(`${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}/ws/control-room`);
    socket.onopen = () => updateState((current) => ({ ...current, connected: true }));
    socket.onclose = () => {
      socket = null;
      updateState((current) => ({ ...current, connected: false }));
    };
    socket.onerror = () => updateState((current) => ({ ...current, connected: false }));
    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as { type?: string; payload?: LiveSnapshotPayload };
        if (payload.type === "snapshot.init" || payload.type === "snapshot.updated") {
          updateState((current) => ({
            ...current,
            overview: payload.payload?.overview ?? current.overview,
            systemMap: payload.payload?.system_map ?? current.systemMap,
            runs: payload.payload?.runs ?? current.runs,
            agents: payload.payload?.agents ?? current.agents,
            portfolio: payload.payload?.portfolio ?? current.portfolio,
            memory: payload.payload?.memory ?? current.memory,
            config: payload.payload?.config ?? current.config,
          }));
        }
      } catch {
        return;
      }
    };
  }

  function disconnectSocket() {
    if (!socket) return;
    socket.close();
    socket = null;
  }

  function startRefresh() {
    if (refreshHandle) return;
    refreshHandle = setInterval(() => {
      if (socket?.readyState === WebSocket.OPEN) return;
      void refreshShell().catch(() => {
        return;
      });
    }, 15000);
  }

  function stopRefresh() {
    if (!refreshHandle) return;
    clearInterval(refreshHandle);
    refreshHandle = null;
  }

  async function init() {
    if (initialized) return;
    initialized = true;
    updateState((current) => ({ ...current, booting: true }));
    try {
      const session = await api.session();
      if (!session.authenticated || !session.csrf_token) {
        updateState((current) => ({
          ...current,
          booting: false,
          authenticated: false,
          csrfToken: "",
          session,
        }));
        return;
      }
      updateState((current) => ({
        ...current,
        authenticated: true,
        csrfToken: session.csrf_token ?? "",
        session,
      }));
      await hydrateCore();
      connectSocket();
      startRefresh();
    } catch (error) {
      updateState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Failed to initialize control room.",
      }));
    } finally {
      updateState((current) => ({ ...current, booting: false }));
    }
  }

  async function login(password: string) {
    updateState((current) => ({ ...current, booting: true, error: "" }));
    try {
      const payload = await api.login(password);
      updateState((current) => ({
        ...current,
        authenticated: true,
        csrfToken: payload.csrf_token,
        session: { authenticated: true, csrf_token: payload.csrf_token },
      }));
      await hydrateCore();
      connectSocket();
      startRefresh();
    } catch (error) {
      updateState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Login failed.",
      }));
    } finally {
      updateState((current) => ({ ...current, booting: false }));
    }
  }

  async function logout() {
    const csrfToken = currentCsrf();
    if (csrfToken) {
      await api.logout(csrfToken).catch(() => {
        return;
      });
    }
    stopRefresh();
    disconnectSocket();
    initialized = false;
    store.set(initialState);
    await init();
  }

  function currentCsrf() {
    let csrfToken = "";
    store.subscribe((value) => {
      csrfToken = value.csrfToken;
    })();
    return csrfToken;
  }

  async function ensurePortfolio() {
    const portfolio = await api.portfolio();
    updateState((current) => ({ ...current, portfolio }));
  }

  async function ensureMemory() {
    const memory = await api.memory();
    updateState((current) => ({ ...current, memory }));
  }

  async function ensureConfig() {
    const config = await api.config();
    updateState((current) => ({ ...current, config }));
  }

  async function ensureRuns() {
    const runs = await api.runs();
    updateState((current) => ({ ...current, runs }));
  }

  async function ensureAgents() {
    const agents = await api.agents();
    updateState((current) => ({ ...current, agents }));
  }

  async function selectAgent(agentId: string) {
    const selectedAgent = await api.agentDetail(agentId);
    updateState((current) => ({ ...current, selectedAgent }));
  }

  async function refreshAll() {
    await Promise.all([hydrateCore()]);
  }

  async function createDeskMessage(rawText: string) {
    const csrfToken = currentCsrf();
    if (!rawText.trim()) return;
    await api.createDeskMessage(csrfToken, rawText);
    await refreshAll();
  }

  async function pauseAutonomy() {
    const csrfToken = currentCsrf();
    await api.pause(csrfToken, "Paused from brutalist command deck");
    await refreshAll();
  }

  async function resumeAutonomy() {
    const csrfToken = currentCsrf();
    await api.resume(csrfToken, "Resumed from brutalist command deck");
    await refreshAll();
  }

  async function runJob(jobName: string) {
    const csrfToken = currentCsrf();
    await api.runJob(csrfToken, jobName);
    await refreshAll();
  }

  async function forceExit(ticker: string, fraction = 1) {
    const csrfToken = currentCsrf();
    await api.forceExit(csrfToken, ticker, fraction);
    await refreshAll();
  }

  function destroy() {
    stopRefresh();
    disconnectSocket();
    initialized = false;
  }

  return {
    subscribe: store.subscribe,
    init,
    login,
    logout,
    ensurePortfolio,
    ensureMemory,
    ensureConfig,
    ensureRuns,
    ensureAgents,
    selectAgent,
    refreshAll,
    refreshShell,
    createDeskMessage,
    pauseAutonomy,
    resumeAutonomy,
    runJob,
    forceExit,
    destroy,
  };
}

export const controlRoom = createControlRoom();
