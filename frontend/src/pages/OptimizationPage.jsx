import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import DashboardHeader from '../components/DashboardHeader.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import OptimizationSuggestions from '../components/OptimizationSuggestions.jsx'
import OptimizedResume from '../components/OptimizedResume.jsx'
import PDFPreview from '../components/PDFPreview.jsx'
import { getJob } from '../services/jobService.js'
import { applyOptimizations, generateFinalResume, getOptimization, refreshPDFAccess } from '../services/optimizationService.js'
import { getApiErrorMessage } from '../services/api.js'

function OptimizationPage() {
  const { optimizationId } = useParams(); const [data, setData] = useState(null); const [job, setJob] = useState(null); const [suggestions, setSuggestions] = useState([]); const [pdf, setPdf] = useState(null); const [loading, setLoading] = useState(true); const [working, setWorking] = useState(false); const [error, setError] = useState('')
  useEffect(() => {
    async function loadSavedOptimization() {
      try {
        const value = await getOptimization(optimizationId)
        setData(value)
        setSuggestions(value.suggestions)
        setJob(await getJob(value.job_id))
        if (value.generated_pdf) {
          try {
            setPdf(await refreshPDFAccess(optimizationId))
          } catch (requestError) {
            setError(getApiErrorMessage(requestError, 'Your PDF is still saved, but its temporary access link could not be restored. Try Restore Saved PDF.'))
          }
        }
      } catch (requestError) {
        setError(getApiErrorMessage(requestError, 'Optimization was not found or is unavailable.'))
      } finally {
        setLoading(false)
      }
    }
    loadSavedOptimization()
  }, [optimizationId])
  function updateSuggestion(id, changes) { setSuggestions((items) => items.map((item) => item.id === id ? { ...item, ...changes } : item)) }
  async function apply() { setWorking(true); setError(''); try { const result = await applyOptimizations(optimizationId, suggestions); setData((current) => ({ ...current, status: 'applied', optimized_resume: result.optimized_resume, after_match: result.match })); setSuggestions((items) => items.map((item) => ({ ...item, status: item.status === 'pending' ? 'rejected' : item.status }))) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to apply these decisions.')) } finally { setWorking(false) } }
  async function generate() { setWorking(true); setError(''); try { const result = await generateFinalResume(optimizationId); setPdf(result); setData((current) => ({ ...current, status: 'generated', generated_pdf: { filename: result.filename } })) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to generate the final PDF.')) } finally { setWorking(false) } }
  async function refresh() { setWorking(true); setError(''); try { setPdf(await refreshPDFAccess(optimizationId)) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to refresh secure PDF access.')) } finally { setWorking(false) } }
  const comparison = data?.before_match && data?.after_match ? { before: data.before_match.overall_score, after: data.after_match.overall_score, change: data.after_match.overall_score - data.before_match.overall_score } : null
  return <div className="min-h-screen bg-slate-50"><DashboardHeader /><main className="mx-auto max-w-5xl px-6 py-12">{loading && <p>Loading optimization...</p>}{error && <ErrorBanner message={error} />}{data?.status === 'suggestions_generated' && <OptimizationSuggestions applying={working} error="" invalidIds={[]} onApply={apply} onChange={updateSuggestion} suggestions={suggestions} />}{data?.generated_pdf && !pdf && <section className="mt-6 rounded-2xl border border-brand-100 bg-white p-6 shadow-card"><p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Saved securely</p><h2 className="mt-1 text-2xl font-black text-ink">Your tailored PDF is saved</h2><p className="mt-2 text-sm text-slate-600">{data.generated_pdf.filename} remains in your account. Restore a fresh secure preview/download link anytime.</p><button className="mt-5 rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white disabled:opacity-60" disabled={working} onClick={refresh} type="button">{working ? 'Restoring…' : 'Restore Saved PDF'}</button></section>}{data?.optimized_resume && !pdf && !data?.generated_pdf && <OptimizedResume company={job?.company || 'Company'} result={{ optimization_id: data.optimization_id, optimized_resume: data.optimized_resume, score_comparison: comparison }} role={job?.role || 'Role'} />}{pdf && comparison && <PDFPreview company={job?.company || 'Company'} loading={working} onBack={() => setPdf(null)} onRefresh={refresh} onRegenerate={generate} pdf={pdf} role={job?.role || 'Role'} scoreComparison={comparison} />}</main></div>
}
export default OptimizationPage
