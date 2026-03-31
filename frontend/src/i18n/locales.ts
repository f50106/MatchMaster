export type Locale = 'zh' | 'en';

export interface Translations {
  // Layout
  appSubtitle: string;
  footerVersion: string;
  backBtn: string;

  // HomePage
  uploadJDTitle: string;
  uploadJDLabel: string;
  parsing: string;
  uploadFailed: string;
  totalEvaluations: string;
  avgScore: string;
  avgTime: string;
  totalCost: string;
  uploadedJDs: string;
  noData: string;
  batchDelete: string;
  selectAll: string;
  cancel: string;
  deleting: string;
  deleteBtnLabel: (n: number) => string;
  confirmDeleteJDs: (n: number) => string;
  deleteFailed: string;
  jdSortNewFirst: string;
  jdSortLastUsed: string;
  jdSortAlpha: string;

  // JDPage
  uploadResumeTitle: string;
  uploadResumeLabel: string;
  evaluating: string;
  evalFailed: string;
  evalRanking: string;
  evalResults: string;
  evalFileName: string;
  sortNewFirst: string;
  sortNewest: string;
  sortOldest: string;
  sortScore: string;
  sortConfidence: string;
  rank: string;
  grade: string;
  score: string;
  confidence: string;
  summary: string;
  duration: string;
  confirmDeleteEvals: (n: number) => string;
  loading: string;

  // EvaluationPage
  reportTitle: string;
  tierLabel: string;
  confidenceLabel: string;
  durationLabel: string;
  scoringNote: string;
  executiveSummary: string;
  coreStrengths: string;
  areasOfConcern: string;
  llmScoring: string;
  deterministicScoring: string;
  llmDimAnalysis: string;
  deterministicBasis: string;
  interviewQuestions: string;
  interviewQsBehavioral: string;
  interviewQsTechnical: string;
  iqFacetTeamRole: string;
  iqFacetWorkAttitude: string;
  iqFacetCrossTeam: string;
  iqFacetStability: string;
  iqFacetProactiveness: string;
  iqFocusLabel: string;
  estimatedCost: string;

  // Dimensions
  dimTechnicalSkills: string;
  dimWorkExperience: string;
  dimEducation: string;
  dimCareerTrajectory: string;
  dimRedFlags: string;
  dimSoftSkills: string;
  dimLanguageFit: string;
  dimSkillMatch: string;
  dimExperience: string;
  dimKeywordOverlap: string;
  dimDepthAnalysis: string;
  dimCareerProgression: string;

  // Tiers
  tierA: string;
  tierB: string;
  tierC: string;
  tierD: string;
  tierF: string;

  // FileUpload
  dragHint: string;
  fileUploading: string;

  // Eval inline status
  evalDate: string;
  evalErrorNotResume: string;
  evalErrorSystem: string;
  loadError: string;
  retry: string;
  evalLLMFailed: string;
  evalLLMFailedDetail: string;
  evalLLMRerun: string;

  // JD inline status
  jdParsing: string;
  evalCount: (n: number) => string;
}

const zh: Translations = {
  appSubtitle: 'AI 履歷篩選工具',
  footerVersion: 'MatchMaster v0.3.0',
  backBtn: '返回',

  uploadJDTitle: '上傳職位描述 (JD)',
  uploadJDLabel: '選擇 JD 檔案 (PDF / DOCX)',
  parsing: '解析中…',
  uploadFailed: '上傳失敗',
  totalEvaluations: '總評估數',
  avgScore: '平均分數',
  avgTime: '平均耗時',
  totalCost: '累計費用',
  uploadedJDs: '已上傳的 JD',
  noData: '尚無資料，請上傳第一份 JD',
  batchDelete: '批量刪除',
  selectAll: '全選',
  cancel: '取消',
  deleting: '刪除中…',
  deleteBtnLabel: (n) => `刪除 (${n})`,
  confirmDeleteJDs: (n) => `確定要刪除所選的 ${n} 筆 JD 及其所有評估紀錄？`,
  deleteFailed: '部分刪除失敗',

  jdSortNewFirst: 'NEW',
  jdSortLastUsed: '最後使用',
  jdSortAlpha: 'JD 名稱',

  uploadResumeTitle: '上傳履歷進行評估',
  uploadResumeLabel: '選擇履歷 (PDF / DOCX)，可多選',
  evaluating: '評估中，請稍候…',
  evalFailed: '評估失敗',
  evalRanking: '評估排名',
  evalResults: '評估結果',
  evalFileName: '檔案名稱',
  sortNewFirst: 'NEW',
  sortNewest: '最新在前',
  sortOldest: '最舊在前',
  sortScore: '按分數',
  sortConfidence: '按信心度',
  rank: '#',
  grade: '評級',
  score: '分數',
  confidence: '信心度',
  summary: '摘要',
  duration: '耗時',
  confirmDeleteEvals: (n) => `確定要刪除所選的 ${n} 筆評估紀錄？`,
  loading: '載入中…',

  reportTitle: '候選人評估報告',
  tierLabel: '級',
  confidenceLabel: '信心度',
  durationLabel: '耗時',
  scoringNote: '確定性評分 × 40%　+　LLM 評分 × 60%',
  executiveSummary: '執行摘要',
  coreStrengths: '核心優勢',
  areasOfConcern: '待關注項目',
  llmScoring: 'LLM 評分',
  deterministicScoring: '確定性評分',
  llmDimAnalysis: 'LLM 維度分析',
  deterministicBasis: '確定性依據',
  interviewQuestions: '建議面試問題',
  interviewQsBehavioral: '人格特質',
  interviewQsTechnical: '技術深度',
  iqFacetTeamRole: '團隊定位',
  iqFacetWorkAttitude: '工作態度',
  iqFacetCrossTeam: '跨團隊能力',
  iqFacetStability: '穩定性與自制力',
  iqFacetProactiveness: '積極度',
  iqFocusLabel: '探測面向',
  estimatedCost: '預估費用',

  dimTechnicalSkills: '技術技能',
  dimWorkExperience: '工作經驗',
  dimEducation: '教育背景',
  dimCareerTrajectory: '職涯軌跡',
  dimRedFlags: '風險燈號',
  dimSoftSkills: '軟實力',
  dimLanguageFit: '語言適配',
  dimSkillMatch: '技能匹配',
  dimExperience: '經驗年資',
  dimKeywordOverlap: '關鍵字重疊',
  dimDepthAnalysis: '履歷真實度',
  dimCareerProgression: '職涯成長',

  tierA: '強烈推薦',
  tierB: '推薦',
  tierC: '待考慮',
  tierD: '不建議',
  tierF: '明顯不符',

  dragHint: '拖曳檔案至此，或點擊選擇',
  fileUploading: '處理中…',
  evalDate: '日期',
  evalErrorNotResume: '檔案不像是履歷，請確認後重新上傳',
  evalErrorSystem: '系統發生錯誤，請稍後再試',
  loadError: '載入失敗',
  retry: '重試',
  evalLLMFailed: 'LLM 評估未完成',
  evalLLMFailedDetail: 'AI 評分解析失敗，各維度顯示為預設值（50 分），結果不可信。',
  evalLLMRerun: '請重新上傳此履歷進行評估以取得正確結果。',
  jdParsing: '解析中…',
  evalCount: (n) => String(n),
};

const en: Translations = {
  appSubtitle: 'AI Resume Screening Tool',
  footerVersion: 'MatchMaster v0.3.0',
  backBtn: 'Back',

  uploadJDTitle: 'Upload Job Description (JD)',
  uploadJDLabel: 'Choose JD file (PDF / DOCX)',
  parsing: 'Parsing…',
  uploadFailed: 'Upload failed',
  totalEvaluations: 'Total Evaluations',
  avgScore: 'Avg. Score',
  avgTime: 'Avg. Duration',
  totalCost: 'Total Cost',
  uploadedJDs: 'Uploaded JDs',
  noData: 'No data yet. Upload your first JD.',
  batchDelete: 'Batch delete',
  selectAll: 'Select all',
  cancel: 'Cancel',
  deleting: 'Deleting…',
  deleteBtnLabel: (n) => `Delete (${n})`,
  confirmDeleteJDs: (n) => `Delete ${n} selected JD(s) and all evaluations?`,
  deleteFailed: 'Some deletions failed',

  jdSortNewFirst: 'NEW',
  jdSortLastUsed: 'Last used',
  jdSortAlpha: 'JD name',

  uploadResumeTitle: 'Upload Resumes for Evaluation',
  uploadResumeLabel: 'Choose resumes (PDF / DOCX), multi-select',
  evaluating: 'Evaluating, please wait…',
  evalFailed: 'Evaluation failed',
  evalRanking: 'Evaluation Ranking',
  evalResults: 'Evaluation Results',
  evalFileName: 'File Name',
  sortNewFirst: 'NEW',
  sortNewest: 'Newest first',
  sortOldest: 'Oldest first',
  sortScore: 'By score',
  sortConfidence: 'By confidence',
  rank: '#',
  grade: 'Grade',
  score: 'Score',
  confidence: 'Confidence',
  summary: 'Summary',
  duration: 'Duration',
  confirmDeleteEvals: (n) => `Delete ${n} selected evaluation(s)?`,
  loading: 'Loading…',

  reportTitle: 'Candidate Evaluation Report',
  tierLabel: '',
  confidenceLabel: 'Confidence',
  durationLabel: 'Duration',
  scoringNote: 'Deterministic × 40%  +  LLM × 60%',
  executiveSummary: 'Executive Summary',
  coreStrengths: 'Core Strengths',
  areasOfConcern: 'Areas of Concern',
  llmScoring: 'LLM Scores',
  deterministicScoring: 'Deterministic Scores',
  llmDimAnalysis: 'LLM Dimension Analysis',
  deterministicBasis: 'Deterministic Basis',
  interviewQuestions: 'Suggested Interview Questions',
  interviewQsBehavioral: 'Soft Skills',
  interviewQsTechnical: 'Technical Depth',
  iqFacetTeamRole: 'Team Role',
  iqFacetWorkAttitude: 'Work Attitude',
  iqFacetCrossTeam: 'Cross-Team',
  iqFacetStability: 'Stability & Discipline',
  iqFacetProactiveness: 'Proactiveness',
  iqFocusLabel: 'Focus',
  estimatedCost: 'Est. Cost',

  dimTechnicalSkills: 'Technical Skills',
  dimWorkExperience: 'Work Experience',
  dimEducation: 'Education',
  dimCareerTrajectory: 'Career Trajectory',
  dimRedFlags: 'Red Flags',
  dimSoftSkills: 'Soft Skills',
  dimLanguageFit: 'Language Fit',
  dimSkillMatch: 'Skill Match',
  dimExperience: 'Experience',
  dimKeywordOverlap: 'Keyword Overlap',
  dimDepthAnalysis: 'Resume Authenticity',
  dimCareerProgression: 'Career Growth',

  tierA: 'Highly Recommended',
  tierB: 'Recommended',
  tierC: 'Consider',
  tierD: 'Not Recommended',
  tierF: 'Poor Fit',

  dragHint: 'Drag files here, or click to browse',
  fileUploading: 'Processing…',
  evalDate: 'Date',
  evalErrorNotResume: 'File cannot be parsed as a resume — please verify and retry',
  evalErrorSystem: 'System error — please try again later',
  loadError: 'Failed to load',
  retry: 'Retry',
  evalLLMFailed: 'LLM Evaluation Incomplete',
  evalLLMFailedDetail: 'AI scoring failed to parse — all dimension scores are defaults (50) and results are unreliable.',
  evalLLMRerun: 'Please re-upload this resume file to re-run the evaluation.',
  jdParsing: 'Parsing…',
  evalCount: (n) => String(n),
};

export const locales: Record<Locale, Translations> = { zh, en };
