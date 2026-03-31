import { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { getEvaluation, type EvaluationDetail } from '../services/api';
import { useI18n } from '../i18n';

// ── Types ──
type DimScore = {
  score: number;
  reasoning?: string;
  evidence?: string[];
  details?: string;
  dimension?: string;
};

const LLM_DIMS = [
  'work_experience', 'technical_skills', 'career_trajectory',
  'soft_skills', 'red_flags', 'education', 'language_fit',
] as const;

const DET_DIMS = [
  'experience', 'skill_match', 'career_progression',
  'depth_analysis', 'red_flags', 'education', 'keyword_overlap',
] as const;

// ── Helpers ──
const stripExt = (name: string) => name.replace(/\.[^/.]+$/, '');

function parseEvidence(e: string): { symbol: string; rest: string; cls: string } {
  if (e.startsWith('✓')) return { symbol: '✓', rest: e.slice(1).trim(), cls: 'text-green-500' };
  if (e.startsWith('△')) return { symbol: '△', rest: e.slice(1).trim(), cls: 'text-amber-400' };
  if (e.startsWith('✗')) return { symbol: '✗', rest: e.slice(1).trim(), cls: 'text-red-400' };
  if (e.startsWith('☆')) return { symbol: '☆', rest: e.slice(1).trim(), cls: 'text-blue-400' };
  return { symbol: '•', rest: e, cls: 'text-gray-300' };
}

function scoreColor(score: number) {
  if (score >= 90) return { bar: 'bg-[#4285F4]', text: 'text-[#4285F4]', ring: '#4285F4' };
  if (score >= 80) return { bar: 'bg-[#34A853]', text: 'text-[#34A853]', ring: '#34A853' };
  if (score >= 70) return { bar: 'bg-[#FBBC04]', text: 'text-[#FBBC04]', ring: '#FBBC04' };
  if (score >= 60) return { bar: 'bg-[#FF6D01]', text: 'text-[#FF6D01]', ring: '#FF6D01' };
  return              { bar: 'bg-[#EA4335]', text: 'text-[#EA4335]', ring: '#EA4335' };
}

function getDimScore(obj: Record<string, unknown>, key: string): DimScore | null {
  const val = obj[key];
  if (typeof val === 'object' && val !== null && 'score' in val) return val as DimScore;
  return null;
}

// ── Score Ring ──
function ScoreRing({ score, color }: { score: number; color: string }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const fill = (Math.min(Math.max(score, 0), 100) / 100) * circ;
  return (
    <svg viewBox="0 0 120 120" className="w-28 h-28 flex-shrink-0">
      <circle cx="60" cy="60" r={r} fill="none" stroke="#f3f4f6" strokeWidth="12" />
      <circle
        cx="60" cy="60" r={r}
        fill="none"
        stroke={color}
        strokeWidth="12"
        strokeLinecap="round"
        strokeDasharray={`${fill} ${circ}`}
        transform="rotate(-90 60 60)"
      />
      <text x="60" y="56" textAnchor="middle" dominantBaseline="middle" fontSize="22" fontWeight="bold" fill="#111827">
        {score.toFixed(1)}
      </text>
      <text x="60" y="74" textAnchor="middle" fontSize="11" fill="#9ca3af">/ 100</text>
    </svg>
  );
}

// ── Score Bar ──
function ScoreBar({ label, score, bar }: { label: string; score: number; bar: string }) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold text-gray-700 tabular-nums">{score.toFixed(1)}</span>
      </div>
      <div className="w-full bg-gray-100 rounded-full h-2">
        <div className={`${bar} h-2 rounded-full transition-all`} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
    </div>
  );
}

// ── Dimension Card (expandable) ──
function DimCard({ name, val, isRed = false, dimLabels }: { name: string; val: DimScore; isRed?: boolean; dimLabels: Record<string, string> }) {
  const [open, setOpen] = useState(false);
  const col = isRed && val.score < 50 ? { bar: 'bg-red-400', text: 'text-red-500' } : scoreColor(val.score);
  const hasContent = !!(val.reasoning?.trim() || val.details?.trim() || (val.evidence?.length ?? 0) > 0);

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm">
      <button
        onClick={() => hasContent && setOpen((o) => !o)}
        className={`w-full px-5 py-4 flex items-center gap-3 text-left ${hasContent ? 'hover:bg-gray-50 cursor-pointer' : 'cursor-default'}`}
      >
        <span className="flex-shrink-0 w-3" />
        <span className="flex-1 font-medium text-gray-800">{dimLabels[name] ?? name}</span>
        <div className="flex items-center gap-3">
          <div className="w-24 bg-gray-100 rounded-full h-1.5 hidden sm:block">
            <div className={`${col.bar} h-1.5 rounded-full`} style={{ width: `${Math.min(val.score, 100)}%` }} />
          </div>
          <span className={`text-sm font-bold w-10 text-right tabular-nums ${col.text}`}>{val.score.toFixed(1)}</span>
          {hasContent && <span className="text-gray-300 text-xs">{open ? '▲' : '▼'}</span>}
        </div>
      </button>
      {open && hasContent && (
        <div className="px-5 pb-4 pt-3 border-t border-gray-100 bg-gray-50 space-y-2">
          {val.reasoning && <p className="text-sm text-gray-700 leading-relaxed">{val.reasoning}</p>}
          {val.details && (
            <p className="text-xs text-gray-500 font-mono bg-gray-100 px-2 py-1 rounded">{val.details}</p>
          )}
          {val.evidence && val.evidence.length > 0 && (
            <ul className="space-y-1 mt-1">
              {val.evidence.map((e, i) => {
                const { symbol, rest, cls } = parseEvidence(e);
                return (
                  <li key={i} className="text-sm text-gray-600 flex items-start gap-2">
                    <span className={`font-bold mt-0.5 flex-shrink-0 ${cls}`}>{symbol}</span>
                    <span>{rest}</span>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main Page ──
export default function EvaluationPage() {
  const { evalId } = useParams<{ evalId: string }>();
  const [ev, setEv] = useState<EvaluationDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { t, locale } = useI18n();

  const dimLabels = useMemo<Record<string, string>>(() => ({
    technical_skills: t.dimTechnicalSkills,
    work_experience:  t.dimWorkExperience,
    education:        t.dimEducation,
    career_trajectory: t.dimCareerTrajectory,
    red_flags:        t.dimRedFlags,
    soft_skills:      t.dimSoftSkills,
    language_fit:     t.dimLanguageFit,
    skill_match:      t.dimSkillMatch,
    experience:       t.dimExperience,
    keyword_overlap:  t.dimKeywordOverlap,
    depth_analysis:   t.dimDepthAnalysis,
    career_progression: t.dimCareerProgression,
  }), [t]);

  const tierInfoMap = useMemo<Record<string, { bg: string; label: string }>>(() => ({
    'A': { bg: 'bg-[#4285F4] text-white',     label: t.tierA },
    'B': { bg: 'bg-[#34A853] text-white',     label: t.tierB },
    'C': { bg: 'bg-[#FBBC04] text-gray-900',  label: t.tierC },
    'D': { bg: 'bg-[#FF6D01] text-white',     label: t.tierD },
    'F': { bg: 'bg-[#EA4335] text-white',     label: t.tierF },
  }), [t]);

  useEffect(() => {
    if (!evalId) return;
    getEvaluation(evalId).then((r) => {
      setEv(r.data);
      // Clear the unread badge for this evaluation
      const jdId = r.data.jd_id;
      if (jdId) {
        // Inline clear to avoid importing the hook (keep it light)
        try {
          const raw = JSON.parse(localStorage.getItem('mm_unread') ?? '{}') as Record<string, string[]>;
          const set = new Set(raw[jdId] ?? []);
          set.delete(evalId);
          if (set.size === 0) delete raw[jdId];
          else raw[jdId] = Array.from(set);
          localStorage.setItem('mm_unread', JSON.stringify(raw));
          window.dispatchEvent(new Event('mm_unread_change'));
        } catch { /* ignore */ }
      }
    }).catch(() => setError(t.loadError ?? 'Failed to load evaluation'));
  }, [evalId]);

  if (error) {
    return (
      <div className="flex flex-col justify-center items-center h-48 gap-3">
        <p className="text-red-500 text-sm">{error}</p>
        <button onClick={() => window.location.reload()} className="px-4 py-2 bg-indigo-500 text-white text-sm rounded-lg hover:bg-indigo-600">
          {t.retry ?? 'Retry'}
        </button>
      </div>
    );
  }

  if (!ev) {
    return (
      <div className="flex justify-center items-center h-48">
        <div className="w-8 h-8 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  // Evaluation pipeline failed — show error card
  if (ev.status === 'failed') {
    return (
      <div className="space-y-4">
        <h1 className="text-xl font-bold text-gray-900 truncate">
          {stripExt(ev.resume_file_name) || t.reportTitle}
        </h1>
        <div className="bg-red-50 border border-red-200 rounded-xl p-6 shadow-sm">
          <h2 className="text-red-600 font-semibold mb-2">&#9888; {t.evalFailed}</h2>
          <p className="text-sm text-red-500 mb-3">{ev.error_message || t.evalErrorSystem}</p>
          <p className="text-sm text-gray-500">{t.evalLLMRerun}</p>
        </div>
      </div>
    );
  }

  const llm = ev.llm_scores as Record<string, unknown> | null;
  const det = ev.deterministic_scores as Record<string, unknown> | null;
  const colors = scoreColor(ev.final_score);
  const tierInfo = tierInfoMap[ev.tier] ?? { bg: 'bg-gray-500 text-white', label: ev.tier };

  // Detect silent LLM parse failure: all 7 dimensions at score=50 with no reasoning
  const _LLM_DIMS = ['technical_skills', 'work_experience', 'education', 'career_trajectory', 'red_flags', 'soft_skills', 'language_fit'];
  const isLLMSilentFail = !!llm && _LLM_DIMS.every(k => {
    const d = llm[k] as Record<string, unknown> | undefined;
    return d && d.score === 50 && !d.reasoning;
  });

  // Extract strengths / weaknesses from LLM scores — locale-aware
  const strengths: string[] = locale === 'zh'
    ? (llm?.strengths_zh as string[] | undefined)?.length ? (llm.strengths_zh as string[]) : (llm?.strengths as string[] | undefined) ?? []
    : (llm?.strengths_en as string[] | undefined)?.length ? (llm.strengths_en as string[]) : (llm?.strengths as string[] | undefined) ?? [];
  const weaknesses: string[] = locale === 'zh'
    ? (llm?.weaknesses_zh as string[] | undefined)?.length ? (llm.weaknesses_zh as string[]) : (llm?.weaknesses as string[] | undefined) ?? []
    : (llm?.weaknesses_en as string[] | undefined)?.length ? (llm.weaknesses_en as string[]) : (llm?.weaknesses as string[] | undefined) ?? [];

  // Meta summary — locale-aware
  const metaSummary: string = locale === 'zh'
    ? (llm?.meta_summary_zh as string || '') || ev.meta_summary
    : (llm?.meta_summary_en as string || '') || ev.meta_summary;

  // Interview questions — handle 5-facet (new), behavioral/technical (legacy), and flat list
  const rawQs = ev.interview_questions;
  const isObj = rawQs && !Array.isArray(rawQs) && typeof rawQs === 'object';

  // 5-facet detection: new format has team_role, work_attitude, etc.
  const FACET_KEYS = ['team_role', 'work_attitude', 'cross_team', 'stability', 'proactiveness'] as const;
  type FacetKey = typeof FACET_KEYS[number];
  interface IQItem { question_en?: string; question_zh?: string; focus?: string; }
  const facetLabelMap: Record<FacetKey, string> = {
    team_role: t.iqFacetTeamRole,
    work_attitude: t.iqFacetWorkAttitude,
    cross_team: t.iqFacetCrossTeam,
    stability: t.iqFacetStability,
    proactiveness: t.iqFacetProactiveness,
  };
  const facetEmojiMap: Record<FacetKey, string> = {
    team_role: '🎯', work_attitude: '⚖️', cross_team: '🤝',
    stability: '🔒', proactiveness: '🚀',
  };

  const is5Facet = isObj && FACET_KEYS.some(k => Array.isArray((rawQs as any)[k]) && (rawQs as any)[k].length > 0);
  const facetQs: Record<FacetKey, IQItem[]> = is5Facet
    ? Object.fromEntries(FACET_KEYS.map(k => [k, ((rawQs as any)[k] ?? []) as IQItem[]])) as Record<FacetKey, IQItem[]>
    : Object.fromEntries(FACET_KEYS.map(k => [k, [] as IQItem[]])) as Record<FacetKey, IQItem[]>;

  // Legacy fallback
  const flatQs = Array.isArray(rawQs) ? rawQs as string[] : [];
  const behavioralQs: string[] = (!is5Facet && isObj) ? ((rawQs as any).behavioral ?? []) : [];
  const technicalQs: string[] = (!is5Facet && isObj) ? ((rawQs as any).technical ?? []) : [];
  const hasQs = is5Facet || flatQs.length > 0 || behavioralQs.length > 0 || technicalQs.length > 0;

  return (
    <div>
      {/* ── Page Title ── */}
      <div className="mb-5">
        <h1 className="text-2xl font-bold text-gray-900 truncate">
          {stripExt(ev.resume_file_name) || t.reportTitle}
        </h1>
      </div>
      <div className="space-y-6 pb-12">

      {/* ── LLM Silent-Fail Warning Banner ── */}
      {isLLMSilentFail && (
        <div className="bg-amber-50 border border-amber-300 rounded-xl p-4 flex gap-3 items-start shadow-sm">
          <span className="text-amber-500 text-xl flex-shrink-0 mt-0.5">&#9888;</span>
          <div>
            <p className="font-semibold text-amber-700 text-sm">{t.evalLLMFailed}</p>
            <p className="text-amber-600 text-sm mt-0.5">{t.evalLLMFailedDetail}</p>
            <p className="text-amber-500 text-xs mt-1">{t.evalLLMRerun}</p>
          </div>
        </div>
      )}

      {/* ── Hero ── */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-6">
          <ScoreRing score={ev.final_score} color={colors.ring} />
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap gap-2">
              <span className={`px-3 py-1 rounded-full text-sm font-bold ${tierInfo.bg}`}>
                {ev.tier} {t.tierLabel} · {tierInfo.label}
              </span>
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                                {t.confidenceLabel} {(ev.confidence * 100).toFixed(0)}%
              </span>
              <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                                {t.durationLabel} {(ev.processing_time_ms / 1000).toFixed(1)}s
              </span>
              {ev.token_usage && (
                <span className="px-3 py-1 bg-gray-100 text-gray-600 rounded-full text-sm">
                  {ev.token_usage.total_tokens?.toLocaleString()} tokens
                </span>
              )}
            </div>
            <p className="text-xs text-gray-400 mt-2">{t.scoringNote}</p>
          </div>
        </div>
      </div>

      {/* ── Executive Summary ── */}
      {metaSummary && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">{t.executiveSummary}</h2>
          <p className="text-gray-700 leading-relaxed">{metaSummary}</p>
        </div>
      )}

      {/* ── Strengths & Weaknesses ── */}
      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="grid sm:grid-cols-2 gap-5">
          {strengths.length > 0 && (
            <div className="bg-white rounded-xl border border-emerald-200 p-5 shadow-sm">
              <h2 className="text-xs font-semibold text-emerald-500 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <span className="text-base">✅</span> {t.coreStrengths}
              </h2>
              <ul className="space-y-2">
                {strengths.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-emerald-400 mt-0.5 flex-shrink-0">●</span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {weaknesses.length > 0 && (
            <div className="bg-white rounded-xl border border-red-200 p-5 shadow-sm">
              <h2 className="text-xs font-semibold text-red-400 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                <span className="text-base">⚠️</span> {t.areasOfConcern}
              </h2>
              <ul className="space-y-2">
                {weaknesses.map((w, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                    <span className="text-red-400 mt-0.5 flex-shrink-0">●</span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* ── Score Overview ── */}
      <div className="grid sm:grid-cols-2 gap-5">
        {llm && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
              {t.llmScoring} <span className="text-gray-300 font-normal normal-case">× 0.65</span>
            </h2>
            <div className="flex flex-col flex-1 justify-between gap-3">
              {LLM_DIMS.map((key) => {
                const d = getDimScore(llm, key);
                if (!d) return null;
                const bar = key === 'red_flags' && d.score < 50 ? 'bg-red-400' : scoreColor(d.score).bar;
                return <ScoreBar key={key} label={dimLabels[key]} score={d.score} bar={bar} />;
              })}
            </div>
          </div>
        )}

        {det && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 shadow-sm flex flex-col">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
              {t.deterministicScoring} <span className="text-gray-300 font-normal normal-case">× 0.35</span>
            </h2>
            <div className="flex flex-col flex-1 justify-between gap-3">
              {DET_DIMS.map((key) => {
                const d = getDimScore(det, key);
                if (!d) return null;
                const bar = key === 'red_flags' && d.score < 50 ? 'bg-red-400' : scoreColor(d.score).bar;
                return <ScoreBar key={key} label={dimLabels[key] ?? key} score={d.score} bar={bar} />;
              })}
            </div>
          </div>
        )}
      </div>

      {/* ── LLM Dimension Deep Dive ── */}
      {llm && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">{t.llmDimAnalysis}</h2>
          <div className="space-y-2">
            {LLM_DIMS.map((key) => {
              const d = getDimScore(llm, key);
              if (!d) return null;
              return <DimCard key={key} name={key} val={d} isRed={key === 'red_flags'} dimLabels={dimLabels} />;
            })}
          </div>
        </div>
      )}

      {/* ── Deterministic Deep Dive ── */}
      {det && (
        <div>
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">{t.deterministicBasis}</h2>
          <div className="space-y-2">
            {DET_DIMS.map((key) => {
              const d = getDimScore(det, key);
              if (!d) return null;
              return <DimCard key={key} name={key} val={d} isRed={key === 'red_flags'} dimLabels={dimLabels} />;
            })}
          </div>
        </div>
      )}

      {/* ── Interview Questions ── */}
      {hasQs && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">{t.interviewQuestions}</h2>

          {/* ── New 5-facet format ── */}
          {is5Facet ? (
            <div className="space-y-6">
              {FACET_KEYS.map(facet => {
                const qs = facetQs[facet];
                if (!qs || qs.length === 0) return null;
                return (
                  <div key={facet}>
                    <h3 className="text-xs font-semibold text-indigo-500 uppercase tracking-widest mb-3">
                      {facetLabelMap[facet]}
                    </h3>
                    <div className="space-y-4">
                      {qs.map((q, i) => {
                        const qText = locale === 'zh' ? (q.question_zh || q.question_en || '') : (q.question_en || q.question_zh || '');
                        return (
                        <div key={i} className="flex gap-3 items-start">
                          <span className="text-indigo-400 flex-shrink-0 mt-1.5 leading-none">●</span>
                          <div className="flex-1 min-w-0">
                            <p className="text-gray-800 text-sm leading-relaxed">{qText}</p>

                          </div>
                        </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : flatQs.length > 0 ? (
            /* ── Legacy: flat list ── */
            <ol className="space-y-3">
              {flatQs.map((q, i) => (
                <li key={i} className="flex gap-3 items-start">
                  <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-50 text-indigo-600 text-xs font-bold flex items-center justify-center mt-0.5">
                    {i + 1}
                  </span>
                  <span className="text-gray-700 text-sm leading-relaxed">{q}</span>
                </li>
              ))}
            </ol>
          ) : (
            /* ── Legacy: behavioral/technical ── */
            <div className="space-y-5">
              {behavioralQs.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-indigo-400 uppercase tracking-widest mb-3">
                    🤝 {t.interviewQsBehavioral}
                  </h3>
                  <ol className="space-y-3">
                    {behavioralQs.map((q, i) => (
                      <li key={i} className="flex gap-3 items-start">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-50 text-indigo-600 text-xs font-bold flex items-center justify-center mt-0.5">
                          {i + 1}
                        </span>
                        <span className="text-gray-700 text-sm leading-relaxed">{q}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
              {technicalQs.length > 0 && (
                <div>
                  <h3 className="text-xs font-semibold text-blue-400 uppercase tracking-widest mb-3">
                    ⚙️ {t.interviewQsTechnical}
                  </h3>
                  <ol className="space-y-3">
                    {technicalQs.map((q, i) => (
                      <li key={i} className="flex gap-3 items-start">
                        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-50 text-blue-600 text-xs font-bold flex items-center justify-center mt-0.5">
                          {i + 1}
                        </span>
                        <span className="text-gray-700 text-sm leading-relaxed">{q}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Token Footer ── */}
      {ev.token_usage && (
        <div className="text-xs text-gray-400 text-center space-x-4 pt-2">
          <span>Prompt {ev.token_usage.prompt_tokens?.toLocaleString()}</span>
          <span>Completion {ev.token_usage.completion_tokens?.toLocaleString()}</span>
          {ev.token_usage.estimated_cost_usd != null && (
            <span>{t.estimatedCost} ${ev.token_usage.estimated_cost_usd.toFixed(4)}</span>
          )}
        </div>
      )}

      </div>
    </div>
  );
}
