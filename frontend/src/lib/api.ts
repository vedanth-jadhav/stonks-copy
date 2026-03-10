export type SessionState = {
  authenticated: boolean;
  csrf_token: string | null;
};

export type MetricMark = {
  mark_date: string;
  portfolio_value: number;
  cash_balance: number;
  realized_pnl: number;
  realized_pnl_today: number;
  total_realized_pnl: number;
  unrealized_pnl: number;
  benchmark_close: number | null;
  benchmark_return_pct: number | null;
  alpha_pct: number | null;
  details: Record<string, unknown>;
};

export type Overview = {
  market: {
    timestamp_utc: string;
    date_local: string;
    time_local: string;
    session_state: string;
    is_market_day: boolean;
  };
  portfolio: {
    cash_balance: number;
    total_deployed: number;
    total_market_value: number;
    portfolio_value: number;
    total_unrealized_pnl: number;
    total_realized_pnl: number;
    total_charges_paid: number;
    open_positions: number;
    priced_positions: number;
    unpriced_positions: number;
  };
  runtime_state: {
    autonomy_paused: boolean;
    entries_blocked: boolean;
    exits_only: boolean;
    updated_at: string | null;
    updated_reason: string | null;
  };
  latest_mark: MetricMark | null;
  scheduler: {
    running: boolean;
    jobs: Array<{ id: string; name: string; next_run_time: string | null; pending: boolean }>;
  };
  latest_jobs: Array<Record<string, unknown>>;
  latest_decisions: Array<Record<string, unknown>>;
  latest_actions: Array<Record<string, unknown>>;
  alerts: string[];
  provider_health: Record<string, unknown>;
};

export type AgentIndexRow = {
  agent_id: string;
  latest_run: Record<string, unknown> | null;
  ic_snapshot: Record<string, unknown>;
  latest_reflection: Record<string, unknown> | null;
};

export type AgentDetail = {
  agent_id: string;
  runs: Array<Record<string, unknown>>;
  signals: Array<Record<string, unknown>>;
  reflections: Array<Record<string, unknown>>;
  ic_snapshot: Record<string, unknown>;
};

export type PortfolioPayload = {
  snapshot: Overview["portfolio"];
  positions: Array<{
    ticker: string;
    shares: number;
    avg_entry_price: number;
    total_cost: number;
    position_type: string;
    stop_loss_price?: number | null;
    trailing_stop_price?: number | null;
    last_updated?: string | null;
  }>;
  orders: Array<Record<string, unknown>>;
  fills: Array<Record<string, unknown>>;
  marks: MetricMark[];
  decisions: Array<Record<string, unknown>>;
};

export type MemoryIndex = {
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
};

export type MemorySearch = {
  query: string;
  results: Array<Record<string, unknown>>;
};

export type ConfigPayload = {
  settings: Record<string, unknown>;
  runtime_state: Overview["runtime_state"];
  active_messages: Array<Record<string, unknown>>;
  operator_actions: Array<Record<string, unknown>>;
  overrides: Record<string, unknown>;
};

export type SystemMetric = {
  id: string;
  label: string;
  value: string;
  tone: string;
};

export type SystemAlert = {
  id: string;
  severity: string;
  title: string;
  detail: string;
  route: string;
};

export type SystemStage = {
  id: string;
  label: string;
  caption: string;
};

export type SystemNode = {
  id: string;
  label: string;
  stage: string;
  route: string;
  status: string;
  metric: { label: string; value: string } | null;
  updated_at: string | null;
  warnings: string[];
  summary: string;
};

export type SystemArtifact = {
  id: string;
  label: string;
  caption: string;
  route: string;
  value: string;
};

export type SystemMapPayload = {
  updated_at: string;
  top_metrics: SystemMetric[];
  alerts: SystemAlert[];
  stages: SystemStage[];
  nodes: SystemNode[];
  boss: {
    label: string;
    status: string;
    value: string;
    caption: string;
    route: string;
  };
  artifacts: SystemArtifact[];
  memory_signal: {
    nodes: number;
    edges: number;
    route: string;
  };
  schedule: Array<{
    id: string;
    label: string;
    value: string | null;
    pending: boolean;
  }>;
};

export type ArtifactFile = {
  relative_path: string;
  size_bytes: number;
  modified_at: string | null;
  exists?: boolean;
};

export type ArtifactFileDetail = ArtifactFile & {
  preview: string;
  truncated: boolean;
  parsed?: unknown;
};

export type GeminiOAuthSettings = {
  binary_path: string;
  effective_binary_path: string;
  binary_exists: boolean;
  auth_dir: string;
  installed_version?: string | null;
  default_login_mode: "google_one" | "code_assist";
  default_project_id: string;
  runtime_base_url: string | null;
  runtime_source: string;
  runtime_status: string;
};

export type GeminiOAuthUsageModel = {
  model_id: string;
  remaining_fraction: number | null;
  remaining_percent: number | null;
  available: boolean;
};

export type GeminiOAuthUsage = {
  checked_at: string | null;
  error: string | null;
  unsupported?: boolean;
  models: GeminiOAuthUsageModel[];
};

export type GeminiOAuthAccount = {
  account_id: string;
  file_name: string;
  email: string;
  project_id: string | null;
  modified_at: string | null;
  size_bytes: number;
  has_refresh_token: boolean;
  status: string;
  usage: GeminiOAuthUsage;
};

export type GeminiOAuthLoginSession = {
  id: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  message: string;
  binary_path: string | null;
  account_id: string | null;
  login_mode: "google_one" | "code_assist";
  project_id: string | null;
  log_path: string | null;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, {
    credentials: "include",
    ...init,
    headers,
  });
  if (!response.ok) {
    let message = `Request failed for ${path}`;
    try {
      const text = await response.text();
      const payload = JSON.parse(text) as { detail?: unknown; message?: unknown };
      const detail = payload.detail ?? payload.message;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail
          .map((item) => {
            if (typeof item === "string") return item;
            if (item && typeof item === "object") {
              const detailMessage = "msg" in item && typeof item.msg === "string" ? item.msg : JSON.stringify(item);
              const detailPath =
                "loc" in item && Array.isArray(item.loc) ? item.loc.map((segment: unknown) => String(segment)).join(".") : "";
              return detailPath ? `${detailPath}: ${detailMessage}` : detailMessage;
            }
            return String(item);
          })
          .join("; ");
      } else if (detail && typeof detail === "object") {
        message = JSON.stringify(detail);
      }
    } catch {
      // JSON parse failed; message stays as default
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export const api = {
  session: () => request<SessionState>("/api/session"),
  login: (password: string) => request<{ ok: boolean; csrf_token: string }>("/api/login", { method: "POST", body: JSON.stringify({ password }) }),
  logout: (csrfToken: string) => request<{ ok: boolean }>("/api/logout", { method: "POST", headers: { "x-csrf-token": csrfToken } }),
  overview: () => request<Overview>("/api/overview"),
  systemMap: () => request<SystemMapPayload>("/api/system-map"),
  runs: () => request<Array<Record<string, unknown>>>("/api/runs"),
  agents: () => request<AgentIndexRow[]>("/api/agents"),
  agentDetail: (agentId: string) => request<AgentDetail>(`/api/agents/${agentId}`),
  portfolio: () => request<PortfolioPayload>("/api/portfolio"),
  memory: () => request<MemoryIndex>("/api/memory"),
  memorySearch: (query: string) => request<MemorySearch>(`/api/memory/search?query=${encodeURIComponent(query)}`),
  config: () => request<ConfigPayload>("/api/config"),
  geminiOAuthSettings: () => request<GeminiOAuthSettings>("/api/gemini-oauth/settings"),
  updateGeminiOAuthSettings: (csrfToken: string, binaryPath: string, loginMode: "google_one" | "code_assist", projectId: string) =>
    request<GeminiOAuthSettings>("/api/gemini-oauth/settings", {
      method: "PUT",
      headers: { "x-csrf-token": csrfToken },
      body: JSON.stringify({ binary_path: binaryPath, login_mode: loginMode, project_id: projectId }),
    }),
  installGeminiOAuthCliProxy: (csrfToken: string) =>
    request<GeminiOAuthSettings>("/api/gemini-oauth/install-cli-proxy", { method: "POST", headers: { "x-csrf-token": csrfToken } }),
  geminiOAuthAccounts: () => request<GeminiOAuthAccount[]>("/api/gemini-oauth/accounts"),
  startGeminiOAuthLogin: (csrfToken: string, loginMode: "google_one" | "code_assist", projectId: string) =>
    request<GeminiOAuthLoginSession>("/api/gemini-oauth/login/start", {
      method: "POST",
      headers: { "x-csrf-token": csrfToken },
      body: JSON.stringify({ login_mode: loginMode, project_id: projectId }),
    }),
  geminiOAuthLoginSession: () => request<GeminiOAuthLoginSession>("/api/gemini-oauth/login/session"),
  refreshGeminiOAuthUsage: (csrfToken: string, accountId: string) =>
    request<GeminiOAuthAccount>(`/api/gemini-oauth/accounts/${encodeURIComponent(accountId)}/refresh-usage`, {
      method: "POST",
      headers: { "x-csrf-token": csrfToken },
    }),
  deleteGeminiOAuthAccount: (csrfToken: string, accountId: string) =>
    request<{ account_id: string; deleted: boolean }>(`/api/gemini-oauth/accounts/${encodeURIComponent(accountId)}`, {
      method: "DELETE",
      headers: { "x-csrf-token": csrfToken },
    }),
  configFiles: () => request<ArtifactFile[]>("/api/config-files"),
  configFileDetail: (relativePath: string) => request<ArtifactFileDetail>(`/api/config-files/${encodeURIComponent(relativePath)}`),
  logs: () => request<ArtifactFile[]>("/api/logs"),
  logDetail: (relativePath: string) => request<ArtifactFileDetail>(`/api/logs/${encodeURIComponent(relativePath)}`),
  reports: () => request<ArtifactFile[]>("/api/reports"),
  reportDetail: (relativePath: string) => request<ArtifactFileDetail>(`/api/reports/${encodeURIComponent(relativePath)}`),
  deskMessages: () => request<Array<Record<string, unknown>>>("/api/desk-messages"),
  pause: (csrfToken: string, reason: string) =>
    request<Overview["runtime_state"]>("/api/control/pause", { method: "POST", headers: { "x-csrf-token": csrfToken }, body: JSON.stringify({ reason }) }),
  resume: (csrfToken: string, reason: string) =>
    request<Overview["runtime_state"]>("/api/control/resume", { method: "POST", headers: { "x-csrf-token": csrfToken }, body: JSON.stringify({ reason }) }),
  createDeskMessage: (csrfToken: string, rawText: string, scope = "global") =>
    request<Record<string, unknown>>("/api/control/desk-messages", {
      method: "POST",
      headers: { "x-csrf-token": csrfToken },
      body: JSON.stringify({ raw_text: rawText, scope }),
    }),
  runJob: (csrfToken: string, jobName: string) =>
    request<Record<string, unknown>>(`/api/control/jobs/${encodeURIComponent(jobName)}/run-now`, {
      method: "POST",
      headers: { "x-csrf-token": csrfToken },
    }),
  forceExit: (csrfToken: string, ticker: string, fraction = 1) =>
    request<Record<string, unknown>>(`/api/control/positions/${encodeURIComponent(ticker)}/${fraction >= 1 ? "exit" : "reduce"}`, {
      method: "POST",
      headers: { "x-csrf-token": csrfToken },
      body: JSON.stringify({ fraction }),
    }),
};
