import { w as writable } from "./index.js";
async function request(path, init) {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body !== void 0) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, {
    credentials: "include",
    ...init,
    headers
  });
  if (!response.ok) {
    let message = `Request failed for ${path}`;
    try {
      const payload = await response.json();
      const detail = payload.detail ?? payload.message;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail.map((item) => {
          if (typeof item === "string") return item;
          if (item && typeof item === "object") {
            const detailMessage = "msg" in item && typeof item.msg === "string" ? item.msg : JSON.stringify(item);
            const detailPath = "loc" in item && Array.isArray(item.loc) ? item.loc.map((segment) => String(segment)).join(".") : "";
            return detailPath ? `${detailPath}: ${detailMessage}` : detailMessage;
          }
          return String(item);
        }).join("; ");
      } else if (detail && typeof detail === "object") {
        message = JSON.stringify(detail);
      }
    } catch {
      message = await response.text();
    }
    throw new Error(message);
  }
  return response.json();
}
const api = {
  session: () => request("/api/session"),
  login: (password) => request("/api/login", { method: "POST", body: JSON.stringify({ password }) }),
  logout: (csrfToken) => request("/api/logout", { method: "POST", headers: { "x-csrf-token": csrfToken } }),
  overview: () => request("/api/overview"),
  systemMap: () => request("/api/system-map"),
  runs: () => request("/api/runs"),
  agents: () => request("/api/agents"),
  agentDetail: (agentId) => request(`/api/agents/${agentId}`),
  portfolio: () => request("/api/portfolio"),
  memory: () => request("/api/memory"),
  memorySearch: (query) => request(`/api/memory/search?query=${encodeURIComponent(query)}`),
  config: () => request("/api/config"),
  geminiOAuthSettings: () => request("/api/gemini-oauth/settings"),
  updateGeminiOAuthSettings: (csrfToken, binaryPath, loginMode, projectId) => request("/api/gemini-oauth/settings", {
    method: "PUT",
    headers: { "x-csrf-token": csrfToken },
    body: JSON.stringify({ binary_path: binaryPath, login_mode: loginMode, project_id: projectId })
  }),
  installGeminiOAuthCliProxy: (csrfToken) => request("/api/gemini-oauth/install-cli-proxy", { method: "POST", headers: { "x-csrf-token": csrfToken } }),
  geminiOAuthAccounts: () => request("/api/gemini-oauth/accounts"),
  startGeminiOAuthLogin: (csrfToken, loginMode, projectId) => request("/api/gemini-oauth/login/start", {
    method: "POST",
    headers: { "x-csrf-token": csrfToken },
    body: JSON.stringify({ login_mode: loginMode, project_id: projectId })
  }),
  geminiOAuthLoginSession: () => request("/api/gemini-oauth/login/session"),
  refreshGeminiOAuthUsage: (csrfToken, accountId) => request(`/api/gemini-oauth/accounts/${encodeURIComponent(accountId)}/refresh-usage`, {
    method: "POST",
    headers: { "x-csrf-token": csrfToken }
  }),
  deleteGeminiOAuthAccount: (csrfToken, accountId) => request(`/api/gemini-oauth/accounts/${encodeURIComponent(accountId)}`, {
    method: "DELETE",
    headers: { "x-csrf-token": csrfToken }
  }),
  configFiles: () => request("/api/config-files"),
  configFileDetail: (relativePath) => request(`/api/config-files/${encodeURIComponent(relativePath)}`),
  logs: () => request("/api/logs"),
  logDetail: (relativePath) => request(`/api/logs/${encodeURIComponent(relativePath)}`),
  reports: () => request("/api/reports"),
  reportDetail: (relativePath) => request(`/api/reports/${encodeURIComponent(relativePath)}`),
  deskMessages: () => request("/api/desk-messages"),
  pause: (csrfToken, reason) => request("/api/control/pause", { method: "POST", headers: { "x-csrf-token": csrfToken }, body: JSON.stringify({ reason }) }),
  resume: (csrfToken, reason) => request("/api/control/resume", { method: "POST", headers: { "x-csrf-token": csrfToken }, body: JSON.stringify({ reason }) }),
  createDeskMessage: (csrfToken, rawText, scope = "global") => request("/api/control/desk-messages", {
    method: "POST",
    headers: { "x-csrf-token": csrfToken },
    body: JSON.stringify({ raw_text: rawText, scope })
  }),
  runJob: (csrfToken, jobName) => request(`/api/control/jobs/${encodeURIComponent(jobName)}/run-now`, {
    method: "POST",
    headers: { "x-csrf-token": csrfToken }
  }),
  forceExit: (csrfToken, ticker, fraction = 1) => request(`/api/control/positions/${encodeURIComponent(ticker)}/${fraction >= 1 ? "exit" : "reduce"}`, {
    method: "POST",
    headers: { "x-csrf-token": csrfToken },
    body: JSON.stringify({ fraction })
  })
};
const initialState = {
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
  config: null
};
function createControlRoom() {
  const store = writable(initialState);
  let refreshHandle = null;
  let socket = null;
  let initialized = false;
  const updateState = (recipe) => store.update(recipe);
  async function hydrateCore() {
    const [overview, systemMap, runs, agents, portfolio, memory, config] = await Promise.all([
      api.overview(),
      api.systemMap(),
      api.runs(),
      api.agents(),
      api.portfolio(),
      api.memory(),
      api.config()
    ]);
    let selectedAgent = null;
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
      error: ""
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
        const payload = JSON.parse(event.data);
        if (payload.type === "snapshot.init" || payload.type === "snapshot.updated") {
          updateState((current) => ({
            ...current,
            overview: payload.payload?.overview ?? current.overview,
            systemMap: payload.payload?.system_map ?? current.systemMap,
            runs: payload.payload?.runs ?? current.runs,
            agents: payload.payload?.agents ?? current.agents,
            portfolio: payload.payload?.portfolio ?? current.portfolio,
            memory: payload.payload?.memory ?? current.memory,
            config: payload.payload?.config ?? current.config
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
    }, 15e3);
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
          session
        }));
        return;
      }
      updateState((current) => ({
        ...current,
        authenticated: true,
        csrfToken: session.csrf_token ?? "",
        session
      }));
      await hydrateCore();
      connectSocket();
      startRefresh();
    } catch (error) {
      updateState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Failed to initialize control room."
      }));
    } finally {
      updateState((current) => ({ ...current, booting: false }));
    }
  }
  async function login(password) {
    updateState((current) => ({ ...current, booting: true, error: "" }));
    try {
      const payload = await api.login(password);
      updateState((current) => ({
        ...current,
        authenticated: true,
        csrfToken: payload.csrf_token,
        session: { authenticated: true, csrf_token: payload.csrf_token }
      }));
      await hydrateCore();
      connectSocket();
      startRefresh();
    } catch (error) {
      updateState((current) => ({
        ...current,
        error: error instanceof Error ? error.message : "Login failed."
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
  async function selectAgent(agentId) {
    const selectedAgent = await api.agentDetail(agentId);
    updateState((current) => ({ ...current, selectedAgent }));
  }
  async function refreshAll() {
    await Promise.all([hydrateCore()]);
  }
  async function createDeskMessage(rawText) {
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
  async function runJob(jobName) {
    const csrfToken = currentCsrf();
    await api.runJob(csrfToken, jobName);
    await refreshAll();
  }
  async function forceExit(ticker, fraction = 1) {
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
    destroy
  };
}
const controlRoom = createControlRoom();
export {
  controlRoom as c
};
