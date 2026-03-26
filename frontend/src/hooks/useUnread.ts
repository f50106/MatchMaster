/**
 * useUnread — tracks "new / unread" evaluation IDs per JD in localStorage.
 * Shape stored: { [jdId]: Set<evalId> }
 * Also tracks which JDs have an unread evaluation (for the homepage badge).
 *
 * Also manages "pending evals" — evals that are still running so any page
 * can subscribe to SSE for them even after navigating away from JDPage.
 * Shape: { [evalId]: jdId }
 */
import { useCallback } from 'react';

const STORAGE_KEY = 'mm_unread';
const PENDING_KEY = 'mm_pending';

// ── Module-level caches to avoid JSON.parse on every callback ──
let _unreadCache: Record<string, string[]> | null = null;
let _unreadRaw: string | null = null;
let _pendingCache: Record<string, string> | null = null;
let _pendingRaw: string | null = null;

function load(): Record<string, string[]> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY) ?? '{}';
    if (raw !== _unreadRaw) {
      _unreadRaw = raw;
      _unreadCache = JSON.parse(raw);
    }
    return _unreadCache!;
  } catch {
    return {};
  }
}

function save(data: Record<string, string[]>) {
  const raw = JSON.stringify(data);
  _unreadRaw = raw;
  _unreadCache = data;
  localStorage.setItem(STORAGE_KEY, raw);
}

function loadPending(): Record<string, string> {
  try {
    const raw = localStorage.getItem(PENDING_KEY) ?? '{}';
    if (raw !== _pendingRaw) {
      _pendingRaw = raw;
      _pendingCache = JSON.parse(raw);
    }
    return _pendingCache!;
  } catch {
    return {};
  }
}

function savePending(data: Record<string, string>) {
  const raw = JSON.stringify(data);
  _pendingRaw = raw;
  _pendingCache = data;
  localStorage.setItem(PENDING_KEY, raw);
}

export function useUnread() {
  /** Mark an evaluation as unread for a given JD. */
  const markUnread = useCallback((jdId: string, evalId: string) => {
    const data = load();
    const set = new Set(data[jdId] ?? []);
    set.add(evalId);
    data[jdId] = Array.from(set);
    save(data);
    // Dispatch a storage event so other tabs/components can react
    window.dispatchEvent(new Event('mm_unread_change'));
  }, []);

  /** Mark all evaluations for a JD as read (clear the badge on that JD). */
  const markJDRead = useCallback((jdId: string) => {
    const data = load();
    delete data[jdId];
    save(data);
    window.dispatchEvent(new Event('mm_unread_change'));
  }, []);

  /** Mark a single evaluation as read. */
  const markEvalRead = useCallback((jdId: string, evalId: string) => {
    const data = load();
    const set = new Set(data[jdId] ?? []);
    set.delete(evalId);
    if (set.size === 0) {
      delete data[jdId];
    } else {
      data[jdId] = Array.from(set);
    }
    save(data);
    window.dispatchEvent(new Event('mm_unread_change'));
  }, []);

  /** Does a JD have any unread evaluations? */
  const hasUnreadForJD = useCallback((jdId: string): boolean => {
    return (load()[jdId]?.length ?? 0) > 0;
  }, []);

  /** Is a specific evaluation unread? */
  const isEvalUnread = useCallback((jdId: string, evalId: string): boolean => {
    return (load()[jdId] ?? []).includes(evalId);
  }, []);

  /** Get all unread eval IDs for a JD. */
  const getUnreadForJD = useCallback((jdId: string): string[] => {
    return load()[jdId] ?? [];
  }, []);

  // ── Pending evals ──────────────────────────────────────────────────────────

  /** Record an eval as pending (still processing). */
  const addPendingEval = useCallback((evalId: string, jdId: string) => {
    const data = loadPending();
    data[evalId] = jdId;
    savePending(data);
    window.dispatchEvent(new Event('mm_pending_change'));
  }, []);

  /** Remove an eval from the pending list (completed or failed). */
  const removePendingEval = useCallback((evalId: string) => {
    const data = loadPending();
    if (!(evalId in data)) return;
    delete data[evalId];
    savePending(data);
    window.dispatchEvent(new Event('mm_pending_change'));
  }, []);

  /** Get all pending evals as { evalId, jdId } pairs. */
  const getPendingEvals = useCallback((): Array<{ evalId: string; jdId: string }> => {
    const data = loadPending();
    return Object.entries(data).map(([evalId, jdId]) => ({ evalId, jdId }));
  }, []);

  return {
    markUnread, markJDRead, markEvalRead,
    hasUnreadForJD, isEvalUnread, getUnreadForJD,
    addPendingEval, removePendingEval, getPendingEvals,
  };
}
