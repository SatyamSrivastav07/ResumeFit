import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import DashboardHeader from '../components/DashboardHeader.jsx'
import ResumeUploader from '../components/ResumeUploader.jsx'
import { useAuth } from '../hooks/useAuth.js'
import { getDashboardHistory } from '../services/dashboardService.js'
import { listResumes } from '../services/resumeService.js'
import { statusLabel } from '../utils/statusLabels.js'

function DashboardPage() {
  const { user } = useAuth()
  const [history, setHistory] = useState([])
  const [resumes, setResumes] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    Promise.all([getDashboardHistory(), listResumes()])
      .then(([historyData, resumeData]) => { setHistory(historyData.items); setResumes(resumeData.items) })
      .catch(() => setError('Unable to load your saved resumes and activity.'))
      .finally(() => setLoading(false))
  }, [])
  return (
    <div className="min-h-screen bg-slate-50">
      <DashboardHeader />
      <main className="mx-auto max-w-6xl px-6 py-12 lg:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div><p className="text-sm font-bold uppercase tracking-[0.16em] text-brand-700">Dashboard</p><h1 className="mt-2 text-4xl font-black text-ink">Welcome</h1><p className="mt-2 text-slate-600">Logged in as <span className="font-bold">{user.email}</span></p></div>
          <a className="rounded-xl bg-brand-600 px-5 py-3 text-center text-sm font-bold text-white" href="#tailor-new">Tailor New Resume</a>
        </div>
        <section className="mt-10" aria-labelledby="saved-resumes-title">
          <div className="flex items-center justify-between"><h2 id="saved-resumes-title" className="text-2xl font-black text-ink">Saved Resumes</h2><Link className="text-sm font-bold text-brand-700" to="/resumes">Manage all</Link></div>
          {!loading && resumes.length === 0 && <p className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-600">No saved resume yet. Upload once below; it will remain available after refresh and future logins.</p>}
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {resumes.slice(0, 4).map((resume) => <article className="flex items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card" key={resume.resume_id}>
              <div className="min-w-0"><h3 className="truncate font-black text-ink">{resume.filename}</h3><p className="mt-1 text-xs text-slate-500">Saved {new Date(resume.created_at).toLocaleDateString()} · {statusLabel(resume.status)}</p></div>
              <Link className="shrink-0 rounded-lg bg-brand-600 px-4 py-2 text-sm font-bold text-white" to={`/resumes/${resume.resume_id}`}>Use Resume</Link>
            </article>)}
          </div>
        </section>
        <section className="mt-10" aria-labelledby="history-title">
          <div className="flex items-center justify-between"><h2 id="history-title" className="text-2xl font-black text-ink">Recent Applications</h2><Link className="text-sm font-bold text-brand-700" to="/resumes">View all resumes</Link></div>
          {loading && <p className="mt-5 text-slate-500">Loading history...</p>}
          {error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}
          {!loading && !error && history.length === 0 && <div className="mt-5 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center"><p className="font-bold text-ink">No tailored resumes yet.</p><a className="mt-3 inline-block text-sm font-bold text-brand-700" href="#tailor-new">Tailor Your First Resume</a></div>}
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            {history.map((item) => <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card" key={item.job_id}>
              <div className="flex items-start justify-between gap-3"><div><h3 className="font-black text-ink">{item.role}</h3><p className="text-sm text-slate-600">{item.company}</p></div><span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-bold text-brand-800">{statusLabel(item.status)}</span></div>
              <p className="mt-4 text-sm text-slate-500">{item.resume_filename}</p>
              <div className="mt-3 flex gap-4 text-sm"><span>Before: <b>{item.before_score ?? '—'}{item.before_score != null ? '%' : ''}</b></span><span>After: <b>{item.after_score ?? '—'}{item.after_score != null ? '%' : ''}</b></span></div>
              <p className="mt-3 text-xs text-slate-400">{new Date(item.created_at).toLocaleDateString()}</p>
              <div className="mt-4 flex flex-wrap gap-3"><Link className="text-sm font-bold text-brand-700" to={item.optimization_id ? `/optimizations/${item.optimization_id}` : `/jobs/${item.job_id}`}>{item.status === 'generated' ? 'View' : 'Continue'}</Link>{item.has_pdf && <Link className="text-sm font-bold text-slate-700" to={`/optimizations/${item.optimization_id}`}>Preview PDF</Link>}</div>
            </article>)}
          </div>
        </section>
        <div id="tailor-new" className="mt-12"><ResumeUploader /></div>
      </main>
    </div>
  )
}
export default DashboardPage
