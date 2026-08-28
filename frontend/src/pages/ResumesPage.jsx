import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import ConfirmModal from '../components/ConfirmModal.jsx'
import DashboardHeader from '../components/DashboardHeader.jsx'
import { deleteResume, listResumes } from '../services/resumeService.js'
import { statusLabel } from '../utils/statusLabels.js'

function ResumesPage() {
  const [items, setItems] = useState([]); const [loading, setLoading] = useState(true); const [deleting, setDeleting] = useState(null); const [error, setError] = useState('')
  useEffect(() => { listResumes().then((data) => setItems(data.items)).catch(() => setError('Unable to load resumes.')).finally(() => setLoading(false)) }, [])
  async function confirmDelete() { try { await deleteResume(deleting.resume_id); setItems((current) => current.filter((item) => item.resume_id !== deleting.resume_id)); setDeleting(null) } catch { setError('Unable to delete this resume.') } }
  return <div className="min-h-screen bg-slate-50"><DashboardHeader /><main className="mx-auto max-w-5xl px-6 py-12"><h1 className="text-3xl font-black text-ink">My Resumes</h1>{loading && <p className="mt-6">Loading resumes...</p>}{error && <p className="mt-5 rounded-xl bg-red-50 p-4 text-red-800">{error}</p>}{!loading && !items.length && <p className="mt-6 rounded-2xl border border-dashed p-8 text-center">No resumes uploaded yet.</p>}<div className="mt-6 space-y-4">{items.map((item) => <article className="flex flex-col gap-4 rounded-2xl border bg-white p-5 sm:flex-row sm:items-center sm:justify-between" key={item.resume_id}><div><h2 className="font-black">{item.filename}</h2><p className="mt-1 text-sm text-slate-500">{statusLabel(item.status)} · {new Date(item.created_at).toLocaleDateString()}</p></div><div className="flex gap-3"><Link className="rounded-lg px-3 py-2 text-sm font-bold text-brand-700" to={`/resumes/${item.resume_id}`}>View</Link><button className="rounded-lg px-3 py-2 text-sm font-bold text-red-700" onClick={() => setDeleting(item)} type="button">Delete</button></div></article>)}</div></main>{deleting && <ConfirmModal title="Delete resume and related history?" description="This permanently deletes the original PDF, tailored PDFs, jobs, and optimizations associated with this resume." onCancel={() => setDeleting(null)} onConfirm={confirmDelete} />}</div>
}
export default ResumesPage
