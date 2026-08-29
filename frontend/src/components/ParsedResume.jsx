function hasText(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function safeHref(value) {
  if (!hasText(value)) return null
  try {
    const parsed = new URL(value)
    return ['http:', 'https:'].includes(parsed.protocol) ? parsed.href : null
  } catch {
    return null
  }
}

function ResumeLink({ children, value }) {
  const href = safeHref(value)
  if (!href) return <span className="break-words">{value}</span>
  return <a className="break-words font-semibold text-brand-700 underline" href={href} rel="noreferrer" target="_blank">{children}</a>
}

function projectLinks(project) {
  const candidates = [
    ['GitHub', project.github_link],
    ['Live Demo', project.live_link],
    [safeHref(project.link)?.includes('github.com') ? 'GitHub' : 'Live Demo', project.link],
  ]
  const seen = new Set()
  return candidates.filter(([, value]) => {
    const href = safeHref(value)
    if (!href || seen.has(href)) return false
    seen.add(href)
    return true
  })
}

function Section({ title, children }) {
  return (
    <section className="border-t border-slate-200 pt-6 first:border-0 first:pt-0">
      <h3 className="text-lg font-black text-ink">{title}</h3>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Bullets({ items }) {
  if (!items?.length) return null
  return (
    <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm leading-6 text-slate-600">
      {items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
    </ul>
  )
}

function DateRange({ start, end }) {
  const values = [start, end].filter(hasText)
  return values.length ? <span>{values.join(' – ')}</span> : null
}

function ParsedResume({ resume }) {
  if (!resume) return null

  const info = resume.personal_info || {}
  const contacts = [
    ['Email', info.email], ['Phone', info.phone], ['Location', info.location],
    ['LinkedIn', info.linkedin], ['GitHub', info.github], ['Portfolio', info.portfolio],
  ].filter(([, value]) => hasText(value))
  const skillGroups = [
    ['Technical', resume.skills?.technical],
    ['Tools', resume.skills?.tools],
    ['Soft skills', resume.skills?.soft],
  ].filter(([, values]) => values?.length)

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8" aria-labelledby="parsed-resume-title">
      <div className="flex items-start gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 font-black text-brand-700" aria-hidden="true">✓</span>
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Structured result</p>
          <h2 id="parsed-resume-title" className="mt-1 text-2xl font-black text-ink">
            {hasText(info.name) ? info.name : 'Parsed Resume'}
          </h2>
        </div>
      </div>

      <div className="mt-7 space-y-7">
        {contacts.length > 0 && (
          <Section title="Contact">
            <dl className="grid gap-3 sm:grid-cols-2">
              {contacts.map(([label, value]) => (
                <div key={label} className="rounded-xl bg-slate-50 px-4 py-3">
                  <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</dt>
                  <dd className="mt-1 break-words text-sm text-slate-800">{['LinkedIn', 'GitHub', 'Portfolio'].includes(label) ? <ResumeLink value={value}>{label}</ResumeLink> : value}</dd>
                </div>
              ))}
            </dl>
          </Section>
        )}

        {hasText(resume.summary) && <Section title="Summary"><p className="text-sm leading-7 text-slate-600">{resume.summary}</p></Section>}

        {skillGroups.length > 0 && (
          <Section title="Skills">
            <div className="space-y-4">
              {skillGroups.map(([label, values]) => (
                <div key={label}>
                  <p className="text-sm font-bold text-slate-700">{label}</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {values.map((value, index) => <span key={`${value}-${index}`} className="rounded-full bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-800">{value}</span>)}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {resume.experience?.length > 0 && (
          <Section title="Experience">
            <div className="space-y-6">
              {resume.experience.map((item, index) => (
                <article key={`${item.company}-${item.role}-${index}`}>
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                    <div><h4 className="font-bold text-ink">{item.role}</h4><p className="text-sm text-slate-600">{item.company}{hasText(item.location) ? ` · ${item.location}` : ''}</p></div>
                    <p className="text-xs font-semibold text-slate-500"><DateRange start={item.start_date} end={item.end_date} /></p>
                  </div>
                  <Bullets items={item.description} />
                </article>
              ))}
            </div>
          </Section>
        )}

        {resume.projects?.length > 0 && (
          <Section title="Projects">
            <div className="space-y-6">
              {resume.projects.map((item, index) => {
                const links = projectLinks(item)
                return <article key={`${item.name}-${index}`}>
                  <h4 className="font-bold text-ink">{item.name}</h4>
                  {links.length > 0 && <div className="mt-1 flex flex-wrap gap-3 text-xs">{links.map(([label, value]) => <ResumeLink key={`${label}-${value}`} value={value}>{label}</ResumeLink>)}</div>}
                  <Bullets items={item.description} />
                  {item.technologies?.length > 0 && <p className="mt-3 text-xs font-semibold text-brand-800">{item.technologies.join(' · ')}</p>}
                </article>
              })}
            </div>
          </Section>
        )}

        {resume.education?.length > 0 && (
          <Section title="Education">
            <div className="space-y-5">
              {resume.education.map((item, index) => (
                <article key={`${item.institution}-${index}`}>
                  <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <h4 className="font-bold text-ink">{item.institution}</h4>
                      <p className="text-sm text-slate-600">{[item.degree, item.field].filter(hasText).join(' · ')}</p>
                      {hasText(item.score) && <p className="mt-1 text-xs text-slate-500">Score: {item.score}</p>}
                    </div>
                    <p className="text-xs font-semibold text-slate-500"><DateRange start={item.start_date} end={item.end_date} /></p>
                  </div>
                </article>
              ))}
            </div>
          </Section>
        )}

        {resume.certifications?.length > 0 && <Section title="Certifications"><Bullets items={resume.certifications} /></Section>}
        {resume.achievements?.length > 0 && <Section title="Achievements"><Bullets items={resume.achievements} /></Section>}
        {resume.languages?.length > 0 && <Section title="Languages"><p className="text-sm text-slate-600">{resume.languages.join(' · ')}</p></Section>}
      </div>
    </section>
  )
}

export default ParsedResume
