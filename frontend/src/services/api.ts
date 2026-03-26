import axios from 'axios';

const api = axios.create({ baseURL: '/api/v1' });

export interface JDSummary {
  id: string;
  title: string;
  file_name?: string;
  status?: string;       // 'parsing' | 'completed'
  eval_count?: number;
  created_at: string | null;
  last_evaluated_at?: string | null;
}

export interface JDDetail extends JDSummary {
  parsed_requirements: Record<string, unknown> | null;
}

export interface EvaluationSummary {
  id: string;
  resume_id: string;
  status: string;
  final_score: number;
  confidence: number;
  tier: string;
  meta_summary: string;
  processing_time_ms: number;
  created_at: string | null;
  error_message?: string;
  resume_file_name?: string;
}

export interface EvaluationDetail extends EvaluationSummary {
  jd_id: string;
  deterministic_scores: Record<string, unknown> | null;
  llm_scores: Record<string, unknown> | null;
  interview_questions: string[] | null;
  token_usage: Record<string, number> | null;
}

export interface CostStats {
  total_evaluations: number;
  avg_score: number;
  avg_processing_ms: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_cost_usd: number;
}

// ── JD ──
export const uploadJD = (file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post<JDDetail & { is_duplicate: boolean }>('/jd', form);
};

export const getJD = (id: string) => api.get<JDDetail>(`/jd/${id}`);

export const listJDs = (limit = 50, offset = 0) =>
  api.get<JDSummary[]>('/jd', { params: { limit, offset } });

export const deleteJD = (id: string) => api.delete(`/jd/${id}`);

// ── Evaluation ──
export const evaluateResume = (jdId: string, file: File) => {
  const form = new FormData();
  form.append('file', file);
  return api.post<EvaluationDetail>(`/jd/${jdId}/evaluate`, form);
};

export const batchEvaluate = (jdId: string, files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append('files', f));
  return api.post(`/jd/${jdId}/evaluate/batch`, form);
};

export const getEvaluation = (id: string) =>
  api.get<EvaluationDetail>(`/evaluations/${id}`);

export const deleteEvaluation = (id: string) =>
  api.delete(`/evaluations/${id}`);

export const listEvaluations = (jdId: string) =>
  api.get<EvaluationSummary[]>(`/jd/${jdId}/evaluations`);

// ── Config ──
export const getConfig = () => api.get('/configs');
export const updateConfig = (data: Record<string, unknown>) =>
  api.put('/configs', data);

// ── Stats ──
export const getCostStats = () => api.get<CostStats>('/stats/cost');

// ── SSE: real-time JD parsing progress ──
export function subscribeJD(
  jdId: string,
  callbacks: {
    onProgress?: () => void;
    onComplete: (data: { id: string; title: string; file_name?: string; created_at?: string | null }) => void;
    onFailed?: (data: { error: string }) => void;
  },
): () => void {
  const es = new EventSource(`/api/v1/jd/${jdId}/stream`);

  es.addEventListener('progress', () => callbacks.onProgress?.());

  es.addEventListener('complete', (e: MessageEvent) => {
    try { callbacks.onComplete(JSON.parse(e.data)); } catch { /* ignore */ }
    es.close();
  });

  es.addEventListener('failed', (e: MessageEvent) => {
    try { callbacks.onFailed?.(JSON.parse(e.data)); } catch { /* ignore */ }
    es.close();
  });

  es.onerror = () => {
    es.close();
    // Fetch the real JD state rather than assuming failure.
    // The SSE connection may have dropped after the JD already completed
    // (very fast parse race: stream closed before EventSource connected).
    fetch(`/api/v1/jd/${jdId}`)
      .then((r) => { if (!r.ok) throw new Error('fetch_failed'); return r.json(); })
      .then((data: { id: string; title: string; file_name?: string; status?: string; created_at?: string | null }) => {
        if (data.status === 'completed') {
          callbacks.onComplete({ id: data.id, title: data.title, file_name: data.file_name, created_at: data.created_at });
        } else if (data.status === 'failed') {
          callbacks.onFailed?.({ error: 'parse_failed' });
        }
        // still 'parsing': leave as-is; SSE may reconnect or user can refresh
      })
      .catch(() => {
        // Network issue — leave card as-is rather than falsely marking failed
      });
  };

  return () => es.close();
}

// ── SSE: real-time eval progress ──
export interface SSECompletePayload {
  status: string;
  final_score?: number;
  tier?: string;
  confidence?: number;
  meta_summary?: string;
  processing_time_ms?: number;
  error_message?: string;
  resume_file_name?: string;
  created_at?: string | null;
}

export function subscribeEvaluation(
  evalId: string,
  callbacks: {
    onProgress?: (data: { status: string }) => void;
    onComplete: (data: SSECompletePayload) => void;
    onFailed?: (data: { status: string; error_message: string }) => void;
  },
): () => void {
  const es = new EventSource(`/api/v1/evaluations/${evalId}/stream`);

  es.addEventListener('progress', (e: MessageEvent) => {
    try { callbacks.onProgress?.(JSON.parse(e.data)); } catch { /* ignore */ }
  });

  es.addEventListener('complete', (e: MessageEvent) => {
    try { callbacks.onComplete(JSON.parse(e.data)); } catch { /* ignore */ }
    es.close();
  });

  es.addEventListener('failed', (e: MessageEvent) => {
    try {
      const d = JSON.parse(e.data);
      callbacks.onFailed?.(d);
    } catch { /* ignore */ }
    es.close();
  });

  es.onerror = () => {
    es.close();
    // Fetch the real eval state rather than assuming failure.
    // The SSE connection may have dropped after the eval already completed.
    fetch(`/api/v1/evaluations/${evalId}`)
      .then((r) => { if (!r.ok) throw new Error('fetch_failed'); return r.json(); })
      .then((data: SSECompletePayload & { status: string }) => {
        if (data.status === 'completed') {
          callbacks.onComplete(data);
        } else if (data.status === 'failed') {
          callbacks.onFailed?.({ status: data.status, error_message: data.error_message ?? '' });
        }
        // pending/processing: leave as-is; the row stays in its current state
      })
      .catch(() => {
        // Truly unreachable — leave row as-is; user can refresh
      });
  };

  return () => es.close();
}

export default api;
