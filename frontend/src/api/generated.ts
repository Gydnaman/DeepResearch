/* Generated from the FastAPI OpenAPI schema. Do not edit by hand. */
export interface components {
  schemas: {
    Citation: {
  citation_id: string;
  run_id: string;
  evidence_id: string;
  section_id: string;
  marker: string
}
    ErrorDetail: {
  code: string;
  message: string;
  retryable?: boolean
}
    ErrorEnvelope: {
  error: components['schemas']['ErrorDetail']
}
    Evidence: {
  evidence_id: string;
  run_id: string;
  source_type: string;
  source_label: string;
  excerpt: string;
  relevance: number;
  is_duplicate?: boolean;
  fixture?: boolean;
  published_at?: string | null;
  conflict_group_id?: string | null
}
    HTTPValidationError: {
  detail?: Array<components['schemas']['ValidationError']>
}
    OutputFormat: 'narrative' | 'executive_summary' | 'bullet_points'
    Plan: {
  run_id: string;
  questions: Array<string>;
  steps: Array<components['schemas']['PlanStep']>;
  created_at: string;
  mode?: string;
  fixture?: boolean
}
    PlanStep: {
  id: string;
  node: string;
  source?: string | null;
  status?: string
}
    ProviderStatus: {
  provider: string;
  kind: string;
  configured: boolean;
  mode?: string;
  fixture?: boolean;
  message: string
}
    Report: {
  run_id: string;
  sections: Array<components['schemas']['ReportSection']>;
  citations?: Array<components['schemas']['Citation']>;
  fixture?: boolean;
  mode?: string;
  warning?: string | null
}
    ReportSection: {
  section_id: string;
  title: string;
  body: string;
  citation_ids?: Array<string>
}
    ResearchEvent: {
  id: number;
  run_id: string;
  event: string;
  phase: string;
  node?: string | null;
  status: string;
  run_status: components['schemas']['RunStatus'];
  summary: string;
  fixture?: boolean;
  created_at?: string;
  task_id?: string | null;
  evidence_ids?: Array<string>;
  error_code?: string | null;
  retryable?: boolean
}
    ResearchRunCreate: {
  topic: string;
  time_range?: components['schemas']['TimeRange'] | null;
  dimensions?: Array<string>;
  output_format?: components['schemas']['OutputFormat'];
  sources?: components['schemas']['ResearchSources'];
  budgets?: components['schemas']['RunBudgets'];
  scenario?: components['schemas']['Scenario'] | null
}
    ResearchRunCreated: {
  run: components['schemas']['ResearchRunSummary'];
  plan: components['schemas']['Plan']
}
    ResearchRunSummary: {
  run_id: string;
  topic: string;
  status: components['schemas']['RunStatus'];
  output_format: components['schemas']['OutputFormat'];
  sources: components['schemas']['ResearchSources'];
  created_at: string;
  updated_at: string;
  mode?: string;
  fixture?: boolean;
  warning?: string | null;
  failure_code?: string | null;
  tokens_used?: number | null
}
    ResearchSources: {
  web?: boolean;
  local?: boolean
}
    RunBudgets: {
  max_reflect_rounds?: number;
  max_scout_calls?: number;
  max_concurrent_scouts?: number;
  max_runtime_seconds?: number;
  max_tokens?: number | null
}
    RunList: {
  items: Array<components['schemas']['ResearchRunSummary']>;
  next_cursor?: string | null
}
    RunStatus: 'planned' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled'
    Scenario: 'success' | 'no_results' | 'partial_scout_failure' | 'writer_error' | 'citation_validation_error' | 'cancel'
    SearchTask: {
  task_id: string;
  run_id: string;
  source: string;
  query_label: string;
  status: string;
  started_at?: string | null;
  completed_at?: string | null;
  evidence_ids?: Array<string>;
  error?: string | null
}
    StreamControlMessage: {
  run_id: string;
  code: string;
  message: string;
  recovery?: string
}
    TimeRange: {
  start: string;
  end: string
}
    ValidationError: {
  loc: Array<string | number>;
  msg: string;
  type: string;
  input?: unknown;
  ctx?: Record<string, unknown>
}
  }
}
