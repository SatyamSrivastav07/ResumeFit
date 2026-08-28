const BREAKDOWN_LABELS = {
  skills: 'Skills',
  experience: 'Experience',
  projects: 'Projects',
  keywords: 'Keywords',
  education: 'Education',
  completeness: 'Completeness',
}

function scoreState(score) {
  if (score >= 85) return { label: 'Strong Match', color: '#047857', text: 'text-emerald-700' }
  if (score >= 70) return { label: 'Good Match', color: '#0f766e', text: 'text-teal-700' }
  if (score >= 50) return { label: 'Moderate Match', color: '#b45309', text: 'text-amber-700' }
  return { label: 'Low Match', color: '#b91c1c', text: 'text-red-700' }
}

function TagSection({ title, items, tone = 'brand', note }) {
  if (!items?.length) return null
  const styles = tone === 'danger'
    ? 'border-red-100 bg-red-50 text-red-800'
    : tone === 'warning'
      ? 'border-amber-100 bg-amber-50 text-amber-800'
      : 'border-brand-100 bg-brand-50 text-brand-800'

  return (
    <section className="border-t border-slate-200 pt-6">
      <h3 className="text-lg font-black text-ink">{title}</h3>
      {note && <p className="mt-2 text-sm leading-6 text-slate-600">{note}</p>}
      <div className="mt-3 flex flex-wrap gap-2">
        {items.map((item, index) => <span key={`${item}-${index}`} className={`rounded-full border px-3 py-1.5 text-xs font-semibold ${styles}`}>{item}</span>)}
      </div>
    </section>
  )
}

function ListSection({ title, items, positive = false }) {
  if (!items?.length) return null
  return (
    <section className="border-t border-slate-200 pt-6">
      <h3 className="text-lg font-black text-ink">{title}</h3>
      <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
        {items.map((item, index) => (
          <li key={`${item}-${index}`} className="flex gap-2">
            <span className={positive ? 'font-black text-brand-700' : 'text-slate-400'} aria-hidden="true">{positive ? '✓' : '•'}</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

function MatchAnalysis({ result }) {
  if (!result?.match) return null
  const match = result.match
  const state = scoreState(match.overall_score)

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8" aria-labelledby="match-analysis-title">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Deterministic analysis</p>
          <h2 id="match-analysis-title" className="mt-1 text-2xl font-black text-ink">Resume Match</h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-slate-600">
            An estimated compatibility score based on the job requirements and information present in your resume.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div
            aria-label={`ResumeFit Match Score ${match.overall_score} out of 100`}
            aria-valuemax="100"
            aria-valuemin="0"
            aria-valuenow={match.overall_score}
            className="grid size-28 shrink-0 place-items-center rounded-full"
            role="progressbar"
            style={{ background: `conic-gradient(${state.color} ${match.overall_score}%, #e2e8f0 0)` }}
          >
            <div className="grid size-20 place-items-center rounded-full bg-white text-center">
              <span className="text-2xl font-black text-ink">{match.overall_score}%</span>
            </div>
          </div>
          <div>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">ResumeFit Match Score</p>
            <p className={`mt-1 text-lg font-black ${state.text}`}>{state.label}</p>
          </div>
        </div>
      </div>

      <section className="mt-8 border-t border-slate-200 pt-6">
        <h3 className="text-lg font-black text-ink">Score Breakdown</h3>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {Object.entries(BREAKDOWN_LABELS).map(([key, label]) => {
            const category = match.breakdown[key]
            return (
              <div key={key} className="rounded-xl bg-slate-50 px-4 py-3">
                <div className="flex items-center justify-between gap-3 text-sm">
                  <span className="font-bold text-slate-700">{label}</span>
                  <span className="font-semibold text-slate-600">
                    {category.applicable ? `${category.score} / ${category.max_score}` : 'Not specified by job'}
                  </span>
                </div>
                {category.applicable && (
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200">
                    <div className="h-full rounded-full bg-brand-600" style={{ width: `${Math.min(100, (category.score / category.max_score) * 100)}%` }} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>

      <div className="mt-7 space-y-6">
        <TagSection title="Matched Skills" items={match.matched_skills} />
        <TagSection
          title="Missing Required Skills"
          items={match.missing_required_skills}
          tone="danger"
          note="These skills were not found in your uploaded resume. ResumeFit will not automatically add them."
        />
        <TagSection title="Missing Preferred Skills" items={match.missing_preferred_skills} tone="warning" />
        <TagSection title="Matched Keywords" items={match.matched_keywords} />
        <TagSection title="Missing Keywords" items={match.missing_keywords} tone="warning" />
        <ListSection title="Relevant Experience" items={match.relevant_experience} positive />
        <ListSection title="Relevant Projects" items={match.relevant_projects} positive />
        <ListSection title="Strengths" items={match.strengths} positive />
        <ListSection title="Gaps" items={match.gaps} />
      </div>

      <p className="mt-7 border-t border-slate-200 pt-5 text-xs leading-5 text-slate-500">
        This estimate does not represent the internal scoring system used by any specific company or ATS.
      </p>
    </section>
  )
}

export default MatchAnalysis
