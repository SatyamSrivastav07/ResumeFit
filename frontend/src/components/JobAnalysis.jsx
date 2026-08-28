function ChipList({ items }) {
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item, index) => (
        <span key={`${item}-${index}`} className="rounded-full bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-800">
          {item}
        </span>
      ))}
    </div>
  )
}

function BulletList({ items }) {
  return (
    <ul className="list-disc space-y-2 pl-5 text-sm leading-6 text-slate-600">
      {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
    </ul>
  )
}

function AnalysisSection({ title, items, bullets = false }) {
  if (!items?.length) return null
  return (
    <section className="border-t border-slate-200 pt-6">
      <h4 className="text-base font-black text-ink">{title}</h4>
      <div className="mt-3">{bullets ? <BulletList items={items} /> : <ChipList items={items} />}</div>
    </section>
  )
}

function JobAnalysis({ result }) {
  if (!result?.analysis) return null
  const analysis = result.analysis

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8" aria-labelledby="job-analysis-title">
      <div className="flex items-start gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 font-black text-brand-700" aria-hidden="true">✓</span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Job analyzed successfully</p>
          <h2 id="job-analysis-title" className="mt-1 text-2xl font-black text-ink">Job Analysis</h2>
          <p className="mt-1 text-sm text-slate-600">{analysis.company} · {analysis.role}</p>
        </div>
      </div>

      <dl className="mt-7 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-slate-50 px-4 py-3">
          <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Experience level</dt>
          <dd className="mt-1 font-semibold text-ink">{analysis.experience_level}</dd>
        </div>
        <div className="rounded-xl bg-slate-50 px-4 py-3">
          <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">Employment type</dt>
          <dd className="mt-1 font-semibold text-ink">{analysis.employment_type}</dd>
        </div>
      </dl>

      <div className="mt-7 space-y-6">
        <AnalysisSection title="Required Skills" items={analysis.required_skills} />
        <AnalysisSection title="Preferred Skills" items={analysis.preferred_skills} />
        <AnalysisSection title="Programming Languages" items={analysis.programming_languages} />
        <AnalysisSection title="Frameworks" items={analysis.frameworks} />
        <AnalysisSection title="Databases" items={analysis.databases} />
        <AnalysisSection title="Cloud & DevOps" items={analysis.cloud_and_devops} />
        <AnalysisSection title="Tools" items={analysis.tools} />
        <AnalysisSection title="Soft Skills" items={analysis.soft_skills} />
        <AnalysisSection title="Responsibilities" items={analysis.responsibilities} bullets />
        <AnalysisSection title="Education Requirements" items={analysis.education_requirements} bullets />
        <AnalysisSection title="Experience Requirements" items={analysis.experience_requirements} bullets />
        <AnalysisSection title="Important Keywords" items={analysis.important_keywords} />
        <AnalysisSection title="Domain Keywords" items={analysis.domain_keywords} />
      </div>

      <div className="mt-7 rounded-xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-900" role="status">
        <p className="font-bold">Job analyzed successfully.</p>
        <p className="mt-1">Next phase will compare this job against the parsed resume. No match score has been calculated.</p>
        <p className="mt-2 break-all text-xs text-brand-800">Temporary Job ID: {result.job_id}</p>
      </div>
    </section>
  )
}

export default JobAnalysis
