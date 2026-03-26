import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import TierBadge from '../components/TierBadge';
import { useI18n } from '../i18n';
import { useUnread } from '../hooks/useUnread';
import {
  getJD,
  evaluateResume,
  batchEvaluate,
  listEvaluations,
  deleteEvaluation,
  subscribeEvaluation,
  type JDDetail,
  type EvaluationSummary,
} from '../services/api';
import type { Translations } from '../i18n/locales';

const PENDING_STATUSES = new Set([
  'pending', 'parsing', 'scoring_deterministic', 'scoring_llm', 'fusing',
]);

const stripExt = (name: string) => name.replace(/\.[^/.]+$/, '');

function classifyEvalError(msg: string | undefined, t: Translations): string {
  if (!msg) return t.evalErrorSystem;
  const lower = msg.toLowerCase();
  // Infrastructure / server errors
  if (
    lower.includes('connection') ||
    lower.includes('timeout') ||
    lower.includes('server error') ||
    lower.includes('502') ||
    lower.includes('503') ||
    lower.includes('database') ||
    lower.includes('redis') ||
    lower.includes('openai') ||
    lower.includes('azure') ||
    lower.includes('api') ||
    lower.includes('rate limit') ||
    lower.includes('authentication')
  ) {
    return t.evalErrorSystem;
  }
  // Only flag as "not a resume" if the backend explicitly says so
  if (lower.includes('not a resume') || lower.includes('document_type')) {
    return t.evalErrorNotResume;
  }
  // Default: treat unknown errors as system errors, not user's fault
  return t.evalErrorSystem;
}

type SortKey = 'new_first' | 'date_desc' | 'date_asc' | 'score' | 'confidence';

export default function JDPage() {
  const { jdId } = useParams<{ jdId: string }>();
  const navigate = useNavigate();
  const { t } = useI18n();
  const { markUnread, markEvalRead, isEvalUnread, addPendingEval, removePendingEval } = useUnread();
  const [jd, setJd] = useState<JDDetail | null>(null);
  const [evaluations, setEvaluations] = useState<EvaluationSummary[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [, setUnreadTick] = useState(0);
  const [justCompleted, setJustCompleted] = useState<Set<string>>(new Set());
  const [sortKey, setSortKey] = useState<SortKey>('date_desc');

  const sortedEvals = useMemo(() => {
    const arr = [...evaluations];
    if (sortKey === 'new_first') {
      return arr.sort((a, b) => {
        const aNew = isEvalUnread(jdId!, a.id) ? 1 : 0;
        const bNew = isEvalUnread(jdId!, b.id) ? 1 : 0;
        if (bNew !== aNew) return bNew - aNew;
        return (b.created_at ?? '').localeCompare(a.created_at ?? '');
      });
    }
    if (sortKey === 'date_desc') return arr.sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
    if (sortKey === 'date_asc')  return arr.sort((a, b) => (a.created_at ?? '').localeCompare(b.created_at ?? ''));
    if (sortKey === 'score')     return arr.sort((a, b) => b.final_score - a.final_score);
    if (sortKey === 'confidence') return arr.sort((a, b) => b.confidence - a.confidence);
    return arr;
  }, [evaluations, sortKey, jdId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!jdId) return;
    getJD(jdId).then((r) => setJd(r.data));
    listEvaluations(jdId).then((r) => setEvaluations(r.data)).catch(() => {});
    // Force re-read of unread state — catches badges written by background SSE
    // that fired mm_unread_change before this page was mounted.
    setUnreadTick((n) => n + 1);
    // No markJDRead here – the per-eval NEW badges clear individually when user
    // clicks into each evaluation row.
  }, [jdId]);

  // Re-render on unread changes
  useEffect(() => {
    const handler = () => setUnreadTick((n) => n + 1);
    window.addEventListener('mm_unread_change', handler);
    return () => window.removeEventListener('mm_unread_change', handler);
  }, []);

  // ── SSE subscription management ──
  // Each pending eval gets one SSE connection. When the backend completes it,
  // the row is updated in-place and marked unread. No page-level polling needed.
  const sseRefs = useRef(new Map<string, () => void>());

  const subscribeToEval = useCallback(
    (evalId: string) => {
      if (sseRefs.current.has(evalId)) return;
      const unsub = subscribeEvaluation(evalId, {
        onProgress: (data) => {
          setEvaluations((prev) =>
            prev.map((ev) => (ev.id === evalId ? { ...ev, status: data.status } : ev)),
          );
        },
        onComplete: (data) => {
          setEvaluations((prev) =>
            prev.map((ev) =>
              ev.id === evalId
                ? {
                    ...ev,
                    status: data.status ?? 'completed',
                    final_score: data.final_score ?? ev.final_score,
                    tier: data.tier ?? ev.tier,
                    confidence: data.confidence ?? ev.confidence,
                    meta_summary: data.meta_summary ?? ev.meta_summary,
                    processing_time_ms: data.processing_time_ms ?? ev.processing_time_ms,
                  }
                : ev,
            ),
          );
          // Mark NEW only on success – user may have navigated away
          if ((data.status ?? 'completed') === 'completed' && jdId) {
            markUnread(jdId, evalId);
            // Flash the row
            setJustCompleted((prev) => new Set(prev).add(evalId));
            setTimeout(
              () => setJustCompleted((prev) => { const n = new Set(prev); n.delete(evalId); return n; }),
              3200,
            );
            // Ask the homepage to refresh eval_count
            window.dispatchEvent(new Event('mm_eval_complete'));
          }
          removePendingEval(evalId);
          sseRefs.current.delete(evalId);
        },
        onFailed: (data) => {
          setEvaluations((prev) =>
            prev.map((ev) =>
              ev.id === evalId
                ? { ...ev, status: 'failed', error_message: data.error_message }
                : ev,
            ),
          );
          sseRefs.current.delete(evalId);
          removePendingEval(evalId);
        },
      });
      sseRefs.current.set(evalId, unsub);
    },
    [jdId, markUnread],
  );

  // Subscribe to any pending evals (initial load or newly added)
  useEffect(() => {
    evaluations.forEach((ev) => {
      if (PENDING_STATUSES.has(ev.status)) subscribeToEval(ev.id);
    });
  }, [evaluations, subscribeToEval]);

  // Close all SSE connections on unmount
  useEffect(() => {
    const refs = sseRefs.current;
    return () => {
      refs.forEach((unsub) => unsub());
      refs.clear();
    };
  }, []);

  // ── Issue 3: upload resolves quickly (backend returns pending eval immediately) ──
  const handleUploadResumes = async (files: File[]) => {
    if (!jdId) return;
    setUploading(true);
    setError('');
    try {
      if (files.length === 1) {
        const res = await evaluateResume(jdId, files[0]);
        const newEval = res.data as EvaluationSummary;
        // Prepend pending row; SSE subscription fires via the evaluations useEffect
        setEvaluations((prev) => {
          const without = prev.filter((e) => e.id !== newEval.id);
          return [newEval, ...without];
        });
        addPendingEval(newEval.id, jdId!);
        // Do NOT markUnread here – SSE fires markUnread when analysis completes
      } else {
        const res = await batchEvaluate(jdId, files);
        const newEvals: EvaluationSummary[] = (res.data.results as EvaluationSummary[]) || [];
        setEvaluations((prev) => {
          const oldIds = new Set(prev.map((e) => e.id));
          const added = newEvals.filter((e) => !oldIds.has(e.id));
          return [...added, ...prev];
        });
        newEvals.forEach((e) => addPendingEval(e.id, jdId!));
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.evalFailed);
    } finally {
      setUploading(false);
    }
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === evaluations.length) setSelected(new Set());
    else setSelected(new Set(evaluations.map((ev) => ev.id)));
  };

  const handleDeleteSelected = async () => {
    if (selected.size === 0) return;
    if (!confirm(t.confirmDeleteEvals(selected.size))) return;
    setDeleting(true);
    try {
      await Promise.all(Array.from(selected).map((id) => deleteEvaluation(id)));
      // Clear unread/NEW state for each deleted eval so the JD badge updates
      if (jdId) {
        Array.from(selected).forEach((id) => markEvalRead(jdId, id));
      }
      setEvaluations((prev) => prev.filter((ev) => !selected.has(ev.id)));
      setSelected(new Set());
      setSelectMode(false);
    } catch {
      alert(t.deleteFailed);
    } finally {
      setDeleting(false);
    }
  };

  const exitSelectMode = () => {
    setSelectMode(false);
    setSelected(new Set());
  };

  // ── Row click: navigate or toggle select; clear unread badge on navigate ──
  const handleRowClick = useCallback(
    (evId: string, isFailed: boolean) => {
      if (isFailed && !selectMode) return; // block navigation on failed rows
      if (selectMode) {
        toggleSelect(evId);
      } else {
        if (jdId) markEvalRead(jdId, evId);
        navigate(`/evaluation/${evId}`);
      }
    },
    [selectMode, navigate, jdId, markEvalRead], // eslint-disable-line react-hooks/exhaustive-deps
  );

  if (!jd) return <p className="text-gray-400">{t.loading}</p>;

  return (
    <div>
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">{jd.file_name ? stripExt(jd.file_name) : jd.title}</h1>

        {/* Upload Resumes */}
        <section>
          <h2 className="text-lg font-semibold mb-3">{t.uploadResumeTitle}</h2>
          <FileUpload
            label={t.uploadResumeLabel}
            multiple
            onFiles={handleUploadResumes}
            disabled={uploading}
          />

          {error && <p className="text-red-500 mt-2">{error}</p>}
        </section>

        {/* Evaluation Rankings */}
        {evaluations.length > 0 && (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">{t.evalResults}</h2>
              <div className="flex items-center gap-2">
                {/* Sort picker */}
                {!selectMode && (
                  <select
                    value={sortKey}
                    onChange={(e) => setSortKey(e.target.value as SortKey)}
                    className="text-xs border border-gray-200 rounded-md px-2 py-1 text-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-300 bg-white cursor-pointer w-32"
                  >
                    <option value="new_first">{t.sortNewFirst}</option>
                    <option value="date_desc">{t.sortNewest}</option>
                    <option value="date_asc">{t.sortOldest}</option>
                    <option value="score">{t.sortScore}</option>
                    <option value="confidence">{t.sortConfidence}</option>
                  </select>
                )}
                {selectMode ? (
                  <>
                    <button
                      onClick={handleDeleteSelected}
                      disabled={selected.size === 0 || deleting}
                      className="px-3 py-1.5 text-sm bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    >
                      {deleting ? t.deleting : t.deleteBtnLabel(selected.size)}
                    </button>
                    <button
                      onClick={exitSelectMode}
                      className="px-3 py-1.5 text-sm bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors"
                    >
                      {t.cancel}
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setSelectMode(true)}
                    className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-red-500 hover:bg-red-50 hover:-translate-y-px hover:shadow-sm transition-all duration-150"
                    title={t.batchDelete}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6" />
                      <path d="M10 11v6" />
                      <path d="M14 11v6" />
                      <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
            <div className="bg-white rounded-lg border overflow-hidden">
              <table className="w-full text-sm table-fixed">
                <colgroup>
                  {selectMode && <col style={{ width: '2.5rem' }} />}
                  <col style={{ width: '2.5rem' }} />
                  <col style={{ width: '6.5rem' }} />
                  <col style={{ width: '5rem' }} />
                  <col style={{ width: '6rem' }} />
                  <col />
                  <col style={{ width: '6.5rem' }} />
                </colgroup>
                <thead className="bg-gray-50 text-gray-500 uppercase text-xs">
                  <tr>
                    {selectMode && (
                      <th className="px-4 py-2 w-10">
                        <input
                          type="checkbox"
                          checked={selected.size === evaluations.length}
                          onChange={toggleSelectAll}
                          onClick={(e) => e.stopPropagation()}
                          className="w-4 h-4 rounded border-gray-300 accent-rose-500 focus:ring-rose-400"
                        />
                      </th>
                    )}
                    <th className="px-4 py-2 text-left">{t.rank}</th>
                    <th className="px-4 py-2 text-left">{t.grade}</th>
                    <th className="px-4 py-2 text-left">{t.score}</th>
                    <th className="px-4 py-2 text-left">{t.confidence}</th>
                    <th className="px-4 py-2 text-left">{t.evalFileName}</th>
                    <th className="px-4 py-2 text-left">{t.evalDate}</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedEvals.map((ev, i) => {
                    const isSelected = selected.has(ev.id);
                    const isNew = jdId ? isEvalUnread(jdId, ev.id) : false;
                    const isPending = PENDING_STATUSES.has(ev.status);
                    const isFailed = ev.status === 'failed';
                    const fileName = ev.resume_file_name ? stripExt(ev.resume_file_name) : (ev.meta_summary || '—');
                    return (
                      <tr
                        key={ev.id}
                        onClick={() => handleRowClick(ev.id, isFailed)}
                        className={[
                          'border-t transition-colors select-none',
                          justCompleted.has(ev.id) ? 'row-complete' : '',
                          isFailed && !selectMode ? 'cursor-not-allowed opacity-90' : 'cursor-pointer',
                          isSelected
                            ? 'bg-red-50 hover:bg-red-100'
                            : selectMode
                              ? 'hover:bg-gray-50'
                              : isFailed
                                ? ''
                                : 'hover:bg-indigo-50',
                        ].join(' ')}
                      >
                        {selectMode && (
                          <td className="px-4 py-2">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onChange={() => toggleSelect(ev.id)}
                              onClick={(e) => e.stopPropagation()}
                              className="w-4 h-4 rounded border-gray-300 accent-rose-500 focus:ring-rose-400"
                            />
                          </td>
                        )}
                        <td className="px-4 py-2 font-mono">{i + 1}</td>

                        {/* Grade — colSpan=3 for failed rows (non-select mode) to show error message */}
                        <td className="px-4 py-2" colSpan={isFailed && !selectMode ? 3 : 1}>
                          {isPending ? (
                            <span className="inline-flex items-center">
                              <svg className="animate-spin h-3.5 w-3.5 text-gray-300" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                              </svg>
                            </span>
                          ) : isFailed && !selectMode ? (
                            <span className="inline-flex items-center gap-1.5 text-red-500 text-xs font-medium">
                              <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                              {classifyEvalError(ev.error_message, t)}
                            </span>
                          ) : isFailed && selectMode ? (
                            <span className="text-red-400 text-base">⚠️</span>
                          ) : (
                            <TierBadge tier={ev.tier} showScore={false} />
                          )}
                        </td>

                        {/* Score — hidden for failed rows in non-select mode */}
                        {!(isFailed && !selectMode) && (
                          <td className="px-4 py-2 font-bold">
                            {isPending || isFailed
                              ? <span className="text-gray-300">—</span>
                              : ev.final_score.toFixed(1)}
                          </td>
                        )}

                        {/* Confidence — hidden for failed rows in non-select mode */}
                        {!(isFailed && !selectMode) && (
                          <td className="px-4 py-2">
                            {isPending || isFailed
                              ? <span className="text-gray-300">—</span>
                              : `${(ev.confidence * 100).toFixed(0)}%`}
                          </td>
                        )}

                        {/* Filename column (replaces summary) */}
                        <td className="px-4 py-2 text-gray-600 truncate">
                          {isPending
                            ? <span className="text-gray-400 animate-pulse text-xs">{fileName}</span>
                            : <span className="text-xs">{fileName}</span>}
                        </td>

                        {/* Date / NEW badge */}
                        <td className="px-4 py-2 text-xs">
                          {isPending ? (
                            <span className="text-gray-300">—</span>
                          ) : isNew ? (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-xs font-bold bg-red-500 text-white leading-none">
                              NEW
                            </span>
                          ) : (
                            ev.created_at
                              ? new Date(ev.created_at).toLocaleDateString()
                              : <span className="text-gray-300">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
