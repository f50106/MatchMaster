import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import { useI18n } from '../i18n';
import { useUnread } from '../hooks/useUnread';
import {
  uploadJD,
  listJDs,
  getCostStats,
  deleteJD,
  subscribeJD,
  subscribeEvaluation,
  type JDSummary,
  type CostStats,
} from '../services/api';

const stripExt = (name: string) => name.replace(/\.[^/.]+$/, '');

export default function HomePage() {
  const navigate = useNavigate();
  const { t } = useI18n();
  const { hasUnreadForJD, markUnread, removePendingEval, getPendingEvals } = useUnread();
  const [jds, setJds] = useState<JDSummary[]>([]);
  const [stats, setStats] = useState<CostStats | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [selectMode, setSelectMode] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [deleting, setDeleting] = useState(false);
  // IDs of JDs that just completed parsing — used to trigger the CSS animation
  const [justCompleted, setJustCompleted] = useState<Set<string>>(new Set());
  const [unreadTick, setUnreadTick] = useState(0);
  type JdSortKey = 'new_first' | 'date' | 'alpha';
  const [jdSortKey, setJdSortKey] = useState<JdSortKey>('new_first');

  const refreshStats = () =>
    getCostStats().then((r) => setStats(r.data)).catch(() => setStats(null));

  useEffect(() => {
    listJDs().then((r) => setJds(r.data));
    refreshStats();
    // Force unread re-read after initial data loads — catches badges written
    // before this page mounted (e.g. eval completed on JDPage while user was there)
    setUnreadTick((n) => n + 1);
  }, []);

  useEffect(() => {
    const handler = () => setUnreadTick((n) => n + 1);
    window.addEventListener('mm_unread_change', handler);
    return () => window.removeEventListener('mm_unread_change', handler);
  }, []);

  // ── Pending eval SSE management ──
  // When the user navigates away from JDPage before an eval finishes,
  // the pending eval ID in localStorage lets HomePage subscribe to its SSE
  // and fire the NEW badge once it completes.
  const [pendingTick, setPendingTick] = useState(0);
  const pendingSseRefs = useRef(new Map<string, () => void>());

  useEffect(() => {
    const handler = () => setPendingTick((n) => n + 1);
    window.addEventListener('mm_pending_change', handler);
    return () => window.removeEventListener('mm_pending_change', handler);
  }, []);

  useEffect(() => {
    const pending = getPendingEvals();
    pending.forEach(({ evalId, jdId }) => {
      if (pendingSseRefs.current.has(evalId)) return;
      const unsub = subscribeEvaluation(evalId, {
        onComplete: (data) => {
          if ((data.status ?? 'completed') === 'completed') {
            markUnread(jdId, evalId);
            window.dispatchEvent(new Event('mm_eval_complete'));
          }
          removePendingEval(evalId);
          pendingSseRefs.current.delete(evalId);
        },
        onFailed: () => {
          removePendingEval(evalId);
          pendingSseRefs.current.delete(evalId);
        },
      });
      pendingSseRefs.current.set(evalId, unsub);
    });
  }, [pendingTick]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const refs = pendingSseRefs.current;
    return () => { refs.forEach((u) => u()); refs.clear(); };
  }, []);

  // When an eval completes (possibly on JDPage or via pending SSE), refresh eval counts + last_evaluated_at
  useEffect(() => {
    const handler = () => {
      // Force re-render so hasUnreadForJD reads fresh localStorage (badge may
      // have been written by JDPage's onComplete while this page wasn't mounted)
      setUnreadTick((n) => n + 1);
      listJDs().then((r) => setJds((prev) => {
        const map = new Map(r.data.map((j) => [j.id, j]));
        return prev.map((j) => {
          if (!map.has(j.id)) return j;
          const updated = map.get(j.id)!;
          return { ...j, eval_count: updated.eval_count, last_evaluated_at: updated.last_evaluated_at };
        });
      })).catch(() => {});
    };
    window.addEventListener('mm_eval_complete', handler);
    return () => window.removeEventListener('mm_eval_complete', handler);
  }, []);

  // ── SSE subscription for pending JD cards ──────────────────────────────────
  const sseRefs = useRef(new Map<string, () => void>());

  const subscribeToJD = useCallback((jdId: string) => {
    if (sseRefs.current.has(jdId)) return;
    const unsub = subscribeJD(jdId, {
      onProgress: () => {
        setJds((prev) =>
          prev.map((j) => (j.id === jdId ? { ...j, status: 'parsing' } : j)),
        );
      },
      onComplete: (data) => {
        setJds((prev) =>
          prev.map((j) =>
            j.id === jdId
              ? {
                  ...j,
                  title: data.title,
                  ...(data.file_name ? { file_name: data.file_name } : {}),
                  status: 'completed',
                  ...(data.created_at != null ? { created_at: data.created_at } : {}),
                }
              : j,
          ),
        );
        // Trigger completion flash animation
        setJustCompleted((prev) => new Set(prev).add(jdId));
        // Remove class after 3.2 s so it can re-trigger if ever needed
        setTimeout(
          () => setJustCompleted((prev) => { const n = new Set(prev); n.delete(jdId); return n; }),
          3200,
        );
        sseRefs.current.delete(jdId);
        refreshStats();
      },
      onFailed: () => {
        setJds((prev) =>
          prev.map((j) => (j.id === jdId ? { ...j, status: 'failed' } : j)),
        );
        sseRefs.current.delete(jdId);
      },
    });
    sseRefs.current.set(jdId, unsub);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Subscribe to any JD that is still parsing
  useEffect(() => {
    jds.forEach((jd) => {
      if (jd.status === 'parsing') subscribeToJD(jd.id);
    });
  }, [jds, subscribeToJD]);

  useEffect(() => {
    const refs = sseRefs.current;
    return () => { refs.forEach((u) => u()); refs.clear(); };
  }, []);

  // ?�?� Upload: returns pending JD immediately, no navigation on complete ?�?�?�?�?�?�?�
  const handleUploadJD = async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const res = await uploadJD(file);
      const newJD = res.data as JDSummary;
      // Prepend pending row; SSE subscription fires via the jds useEffect
      setJds((prev) => {
        const without = prev.filter((j) => j.id !== newJD.id);
        return [{ ...newJD, eval_count: 0 }, ...without];
      });
      // Note: navigation is intentionally removed. User stays on the home page
      // and sees the parsing?�state card update live.
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t.uploadFailed);
    } finally {
      setUploading(false);
    }
  };

  const toggleSelect = (id: string) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });

  const toggleSelectAll = () =>
    selected.size === jds.length
      ? setSelected(new Set())
      : setSelected(new Set(jds.map((jd) => jd.id)));

  const handleDeleteSelected = async () => {
    if (selected.size === 0) return;
    if (!confirm(t.confirmDeleteJDs(selected.size))) return;
    setDeleting(true);
    try {
      await Promise.all(Array.from(selected).map((id) => deleteJD(id)));
      setJds((prev) => prev.filter((jd) => !selected.has(jd.id)));
      setSelected(new Set());
      setSelectMode(false);
      refreshStats();
    } catch {
      alert(t.deleteFailed);
    } finally {
      setDeleting(false);
    }
  };

  const exitSelectMode = () => { setSelectMode(false); setSelected(new Set()); };

  // ── Sorted JD list ─────────────────────────────────────────────────────────
  // unreadTick in deps ensures the sort re-runs when unread state changes
  const sortedJds = useMemo(() => {
    const arr = [...jds];
    if (jdSortKey === 'new_first') {
      return arr.sort((a, b) => {
        const aNew = hasUnreadForJD(a.id) ? 1 : 0;
        const bNew = hasUnreadForJD(b.id) ? 1 : 0;
        if (bNew !== aNew) return bNew - aNew;
        const aDate = a.last_evaluated_at ?? a.created_at ?? '';
        const bDate = b.last_evaluated_at ?? b.created_at ?? '';
        return bDate.localeCompare(aDate);
      });
    }
    if (jdSortKey === 'date') {
      return arr.sort((a, b) => {
        const aDate = a.last_evaluated_at ?? a.created_at ?? '';
        const bDate = b.last_evaluated_at ?? b.created_at ?? '';
        return bDate.localeCompare(aDate);
      });
    }
    if (jdSortKey === 'alpha') {
      return arr.sort((a, b) => a.title.localeCompare(b.title));
    }
    return arr;
  }, [jds, jdSortKey, unreadTick]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleRowClick = useCallback(
    (id: string, isPending: boolean) => {
      if (selectMode) { toggleSelect(id); return; }
      if (isPending) return; // can't open a JD that is still parsing
      navigate(`/jd/${id}`);
    },
    [selectMode, navigate], // eslint-disable-line react-hooks/exhaustive-deps
  );

  return (
    <div className="space-y-6">
      {/* Upload JD */}
      <section>
        <h2 className="text-lg font-semibold mb-3">{t.uploadJDTitle}</h2>
        <FileUpload
          label={t.uploadJDLabel}
          onFiles={handleUploadJD}
          disabled={uploading}
        />
        {error && <p className="text-red-500 mt-2">{error}</p>}
      </section>

      {/* Stats */}
      {stats && stats.total_evaluations > 0 && (
        <section className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label={t.totalEvaluations} value={stats.total_evaluations} />
          <StatCard label={t.avgScore} value={stats.avg_score.toFixed(1)} />
          <StatCard label={t.avgTime} value={`${(stats.avg_processing_ms / 1000).toFixed(1)}s`} />
          <StatCard label={t.totalCost} value={`$${stats.total_cost_usd.toFixed(4)}`} />
        </section>
      )}

      {/* JD List */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">{t.uploadedJDs}</h2>
          {jds.length > 0 && (
            <div className="flex items-center gap-2">
              {/* JD sort selector — only when not in select mode */}
              {!selectMode && (
                <select
                  value={jdSortKey}
                  onChange={(e) => setJdSortKey(e.target.value as JdSortKey)}
                  className="text-xs text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-300 cursor-pointer w-24"
                >
                  <option value="new_first">{t.jdSortNewFirst}</option>
                  <option value="date">{t.jdSortLastUsed}</option>
                  <option value="alpha">{t.jdSortAlpha}</option>
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
                    <path d="M10 11v6" /><path d="M14 11v6" />
                    <path d="M9 6V4a1 1 0 011-1h4a1 1 0 011 1v2" />
                  </svg>
                </button>
              )}
            </div>
          )}
        </div>

        {jds.length === 0 ? (
          <p className="text-gray-400">{t.noData}</p>
        ) : (
          <div className="space-y-2">
            {selectMode && (
              <div
                onClick={toggleSelectAll}
                className="flex items-center gap-3 px-4 py-2 text-sm text-gray-500 cursor-pointer select-none rounded-lg hover:bg-gray-50"
              >
                <input
                  type="checkbox"
                  checked={selected.size === jds.length}
                  onChange={toggleSelectAll}
                  onClick={(e) => e.stopPropagation()}
                  className="w-4 h-4 rounded border-gray-300 accent-rose-500 focus:ring-rose-400"
                />
                {t.selectAll}
              </div>
            )}
            {sortedJds.map((jd) => {
              const isSelected = selected.has(jd.id);
              const isPending = jd.status === 'parsing';
              const isFailed = jd.status === 'failed';
              const hasNew = !isPending && hasUnreadForJD(jd.id);
              const isFlashing = justCompleted.has(jd.id);
              const count = jd.eval_count ?? 0;

              return (
                <div
                  key={jd.id}
                  onClick={() => handleRowClick(jd.id, isPending)}
                  className={[
                    'flex items-center rounded-lg border px-4 py-3 transition-colors select-none',
                    isFlashing ? 'card-complete' : '',
                    isSelected
                      ? 'bg-red-50 border-red-200 hover:bg-red-100 cursor-pointer'
                      : isPending || isFailed
                        ? 'bg-gray-50 border-gray-200 cursor-default'
                        : selectMode
                          ? 'bg-white border-gray-200 hover:bg-gray-50 cursor-pointer'
                          : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-indigo-200 cursor-pointer',
                  ].join(' ')}
                >
                  {selectMode && (
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelect(jd.id)}
                      onClick={(e) => e.stopPropagation()}
                      className="mr-3 w-4 h-4 rounded border-gray-300 accent-rose-500 focus:ring-rose-400 flex-shrink-0"
                    />
                  )}

                  {/* Filename + pending state */}
                  <span className="flex-1 font-medium min-w-0 truncate">
                    {isPending ? (
                      <span className="flex items-center gap-2 text-gray-400">
                        <svg className="animate-spin h-3.5 w-3.5 flex-shrink-0" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        <span className="animate-pulse">{jd.file_name ? stripExt(jd.file_name) : jd.title || t.jdParsing}</span>
                      </span>
                    ) : isFailed ? (
                      <span className="text-red-400">{jd.file_name ? stripExt(jd.file_name) : jd.title}</span>
                    ) : (
                      jd.file_name ? stripExt(jd.file_name) : jd.title
                    )}
                  </span>

                  {/* Right section: NEW + count chip + date — fixed widths so NEW never shifts */}
                  <div className="flex items-center ml-3 gap-2 flex-shrink-0">
                    {/* NEW badge — always occupies the same fixed width slot */}
                    <span className={`inline-flex items-center justify-center w-10 ${hasNew ? '' : 'invisible'}`}>
                      <span className="px-1.5 py-0.5 rounded-full text-xs font-bold bg-red-500 text-white leading-none">
                        NEW
                      </span>
                    </span>

                    {/* Eval count chip — fixed width, purely numeric so it's stable across languages */}
                    {!isPending && !isFailed ? (
                      <span className={`text-xs rounded-full w-10 h-5 inline-flex items-center justify-center tabular-nums ${
                        count === 0
                          ? 'bg-gray-100 text-gray-400'
                          : 'bg-indigo-50 text-indigo-600 font-medium'
                      }`}>
                        {t.evalCount(count)}
                      </span>
                    ) : (
                      <span className="w-10" />
                    )}

                    {/* Date */}
                    <span className="text-xs text-gray-400 w-20 text-right">
                      {(() => {
                        const d = jd.last_evaluated_at ?? jd.created_at;
                        return d ? new Date(d).toLocaleDateString() : '';
                      })()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white rounded-lg border p-4 text-center">
      <p className="text-2xl font-bold text-indigo-600">{value}</p>
      <p className="text-sm text-gray-500">{label}</p>
    </div>
  );
}


