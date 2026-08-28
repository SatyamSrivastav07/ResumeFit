import { useState } from 'react'

const SECTION_LABELS = {
  summary: 'Summary',
  experience: 'Experience',
  projects: 'Project',
  skills: 'Skills & Tools',
}

function OptimizationSuggestions({ suggestions, onChange, onApply, applying, error, invalidIds = [] }) {
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState('')
  const approvedCount = suggestions.filter((item) => ['accepted', 'edited'].includes(item.status)).length
  const pendingCount = suggestions.filter((item) => item.status === 'pending').length

  function startEdit(suggestion) {
    setEditingId(suggestion.id)
    setDraft(suggestion.suggested)
  }

  function saveEdit(suggestion) {
    const cleaned = draft.trim()
    if (!cleaned) return
    onChange(suggestion.id, { suggested: cleaned, status: 'edited' })
    setEditingId(null)
    setDraft('')
  }

  if (!suggestions.length) {
    return (
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
        <h2 className="text-xl font-black text-ink">No safe suggestions generated</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">ResumeFit did not find a sufficiently grounded rewrite to recommend. No content was changed.</p>
      </section>
    )
  }

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8" aria-labelledby="optimization-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">AI suggestions · Human controlled</p>
          <h2 id="optimization-title" className="mt-1 text-2xl font-black text-ink">Review Targeted Changes</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Accept, reject, or edit each suggestion. Pending and rejected changes are never applied.</p>
        </div>
        <p className="shrink-0 rounded-full bg-brand-50 px-4 py-2 text-sm font-bold text-brand-800">{approvedCount} / {suggestions.length} changes approved</p>
      </div>

      <div className="mt-7 space-y-5">
        {suggestions.map((suggestion, index) => {
          const invalid = invalidIds.includes(suggestion.id)
          const editing = editingId === suggestion.id
          const confirmation = suggestion.type === 'confirm_technical_skill' || suggestion.type === 'confirm_tool_skill'
          return (
            <article key={suggestion.id} className={`rounded-2xl border p-5 ${invalid ? 'border-red-300 bg-red-50/40' : 'border-slate-200 bg-slate-50/60'}`}>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="text-xs font-black uppercase tracking-[0.14em] text-brand-700">{index + 1}. {SECTION_LABELS[suggestion.section] || suggestion.section}</p>
                <span className={`rounded-full px-3 py-1 text-xs font-bold capitalize ${suggestion.status === 'accepted' || suggestion.status === 'edited' ? 'bg-emerald-100 text-emerald-800' : suggestion.status === 'rejected' ? 'bg-slate-200 text-slate-700' : 'bg-amber-100 text-amber-800'}`}>{suggestion.status}</span>
              </div>

              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-200 bg-white p-4">
                  <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Original</p>
                  <p className="mt-2 text-sm leading-6 text-slate-700">{suggestion.original}</p>
                </div>
                <div className="rounded-xl border border-brand-100 bg-brand-50 p-4">
                  <p className="text-xs font-bold uppercase tracking-wide text-brand-700">Suggested</p>
                  {editing ? (
                    <textarea
                      aria-label="Edit suggested resume wording"
                      className="mt-2 min-h-32 w-full resize-y rounded-lg border border-brand-200 bg-white px-3 py-2 text-sm leading-6 text-ink"
                      maxLength={2000}
                      onChange={(event) => setDraft(event.target.value)}
                      value={draft}
                    />
                  ) : <p className="mt-2 text-sm leading-6 text-slate-700">{suggestion.suggested}</p>}
                </div>
              </div>

              <div className="mt-4 rounded-xl bg-white p-4 text-sm leading-6 text-slate-600">
                <p><span className="font-bold text-slate-800">Why this helps:</span> {suggestion.reason}</p>
                {suggestion.matched_job_keywords.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {suggestion.matched_job_keywords.map((keyword, keywordIndex) => <span key={`${keyword}-${keywordIndex}`} className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-800">{keyword}</span>)}
                  </div>
                )}
                <p className="mt-3 text-xs text-slate-500"><span className="font-bold">Grounded in:</span> {suggestion.evidence.join(' · ')}</p>
              </div>

              {confirmation && <div className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><p className="font-black">Confirm this skill truthfully</p><p className="mt-1">This skill was not found in your uploaded resume. Accept it only if you genuinely know or have used it; your approval will add it to the Skills section.</p></div>}

              {invalid && <p className="mt-4 text-sm font-semibold text-red-800">This edit introduces information that could not be verified from your original resume.</p>}

              <div className="mt-5 flex flex-wrap gap-3">
                {editing ? (
                  <>
                    <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700" onClick={() => saveEdit(suggestion)} type="button">Save Edit</button>
                    <button className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100" onClick={() => setEditingId(null)} type="button">Cancel</button>
                  </>
                ) : (
                  <>
                    <button className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white hover:bg-brand-700" onClick={() => onChange(suggestion.id, { status: 'accepted' })} type="button">{confirmation ? 'Yes, I Have This Skill' : 'Accept'}</button>
                    <button className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-100" onClick={() => onChange(suggestion.id, { status: 'rejected' })} type="button">{confirmation ? 'No, Don’t Add' : 'Reject'}</button>
                    <button className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-bold text-brand-800 hover:bg-brand-100" onClick={() => startEdit(suggestion)} type="button">Edit</button>
                  </>
                )}
              </div>
            </article>
          )
        })}
      </div>

      {error && <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">{error}</div>}

      <div className="mt-7 border-t border-slate-200 pt-6">
        <button
          className="rounded-xl bg-ink px-5 py-3 text-sm font-bold text-white shadow-lg hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={applying || approvedCount === 0 || pendingCount > 0 || Boolean(editingId)}
          onClick={onApply}
          type="button"
        >
          {applying ? 'Applying approved changes…' : pendingCount > 0 ? `Review ${pendingCount} Remaining Change${pendingCount === 1 ? '' : 's'}` : 'Apply Approved Changes'}
        </button>
        <p className="mt-3 text-xs leading-5 text-slate-500">You must accept, reject, or edit every suggestion before applying. ResumeFit only applies approved changes supported by your original resume; missing skills are never automatically added.</p>
      </div>
    </section>
  )
}

export default OptimizationSuggestions
