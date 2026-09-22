const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8009";
const TOKEN_KEY = "rootcause_token";

export type ApiResult<T> = {
  success: boolean;
  data?: T;
  error?: { code: string; message: string };
};

function authHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<ApiResult<T>> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init?.headers || {}),
    },
  });
  const json = (await res.json()) as ApiResult<T> & { detail?: unknown };
  if (!res.ok) {
    let message = res.statusText;
    if (json.error?.message) message = json.error.message;
    else if (typeof json.detail === "string") message = json.detail;
    else if (Array.isArray(json.detail) && json.detail[0]?.msg) message = String(json.detail[0].msg);
    return {
      success: false,
      error: { code: json.error?.code || "HTTP_ERROR", message },
    };
  }
  return json;
}

export type User = {
  id: string;
  email: string;
  full_name: string;
  role: string;
};

export type EvidenceItem = {
  id: string;
  source: string;
  tool: string;
  summary: string;
  relevance?: number | null;
};

export type Hypothesis = {
  statement: string;
  confidence: number;
  evidence_ids: string[];
  rationale: string;
};

export type InvestigationStep = {
  order: number;
  action: string;
  reason: string;
  related_evidence_ids: string[];
};

export type InvestigationReport = {
  investigation_id: string;
  title: string;
  symptom: string;
  service?: string | null;
  environment: string;
  status: string;
  llm_provider: string;
  tools_invoked: string[];
  evidence: EvidenceItem[];
  primary_hypothesis: Hypothesis | null;
  alternate_hypotheses: Hypothesis[];
  recommended_investigation: InvestigationStep[];
  warnings: string[];
  created_at: string;
  completed_at?: string | null;
};

export type InvestigationSummary = {
  id: string;
  title: string;
  symptom: string;
  service?: string | null;
  environment: string;
  status: string;
  confidence?: number | null;
  created_at: string;
  completed_at?: string | null;
};

export const api = {
  login: async (email: string, password: string) => {
    const res = await request<{ user: User; access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (res.success && res.data?.access_token) {
      localStorage.setItem(TOKEN_KEY, res.data.access_token);
    }
    return res;
  },
  me: () => request<User>("/api/auth/me"),
  logout: async () => {
    const res = await request("/api/auth/logout", { method: "POST" });
    localStorage.removeItem(TOKEN_KEY);
    return res;
  },
  listInvestigations: () => request<InvestigationSummary[]>("/api/investigations"),
  createInvestigation: (body: {
    title: string;
    symptom: string;
    service?: string;
    environment?: string;
    time_window_minutes?: number;
  }) =>
    request<InvestigationReport>("/api/investigations", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  getInvestigation: (id: string) =>
    request<InvestigationReport>(`/api/investigations/${id}`),
  health: () =>
    request<{ status: string; database: boolean; llm_provider: string }>("/api/health"),
};
