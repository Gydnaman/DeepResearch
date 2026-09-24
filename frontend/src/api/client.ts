import type {
  CreateRunBody,
  Evidence,
  Plan,
  ProviderStatus,
  Report,
  RunPage,
  RunSummary,
  SearchTask,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => null)
    throw new Error(payload?.error?.message ?? payload?.detail?.message ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  create: (body: CreateRunBody) => request<{ run: RunSummary; plan: Plan }>('/research-runs', { method: 'POST', body: JSON.stringify(body) }),
  getRun: (id: string) => request<RunSummary>(`/research-runs/${id}`),
  getPlan: (id: string) => request<Plan>(`/research-runs/${id}/plan`),
  start: (id: string) => request<RunSummary>(`/research-runs/${id}/start`, { method: 'POST', body: '{}' }),
  cancel: (id: string) => request<RunSummary>(`/research-runs/${id}/cancel`, { method: 'POST', body: '{}' }),
  evidence: (id: string) => request<Evidence[]>(`/research-runs/${id}/evidence`),
  report: (id: string) => request<Report>(`/research-runs/${id}/report`),
  tasks: (id: string) => request<SearchTask[]>(`/research-runs/${id}/search-tasks`),
  history: (limit = 20, cursor?: string) => request<RunPage>(`/research-runs?limit=${limit}${cursor ? `&cursor=${encodeURIComponent(cursor)}` : ''}`),
  providers: () => request<ProviderStatus[]>('/providers/status'),
}
