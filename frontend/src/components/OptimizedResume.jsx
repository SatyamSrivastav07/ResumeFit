import { useState } from 'react'

import { generateFinalResume, refreshPDFAccess } from '../services/optimizationService.js'
import ParsedResume from './ParsedResume.jsx'
import PDFPreview from './PDFPreview.jsx'

function OptimizedResume({ company, result, role }) {
  const [generatingPDF, setGeneratingPDF] = useState(false)
  const [pdfError, setPDFError] = useState('')
  const [pdfResult, setPDFResult] = useState(null)
  if (!result?.optimized_resume) return null
  const comparison = result.score_comparison
  const changeLabel = comparison.change > 0
    ? `+${comparison.change} points`
    : comparison.change < 0
      ? `${comparison.change} points`
      : 'No score change'
  const changeStyle = comparison.change > 0
    ? 'text-emerald-700'
    : comparison.change < 0
      ? 'text-red-700'
      : 'text-slate-600'

  async function handleGeneratePDF() {
    if (generatingPDF) return
    setGeneratingPDF(true)
    setPDFError('')
    try {
      const response = await generateFinalResume(result.optimization_id)
      setPDFResult(response)
    } catch (error) {
      const status = error.response?.status
      if (status === 401) setPDFError('Your session could not be verified. Log in again and retry.')
      else if (status === 422) setPDFError('The optimized resume data is invalid. Apply the changes again and retry.')
      else if (status === 503) setPDFError('Secure PDF storage is temporarily unavailable. Please try again.')
      else setPDFError('PDF generation failed. Please try again.')
    } finally {
      setGeneratingPDF(false)
    }
  }

  async function handleRefreshAccess() {
    if (generatingPDF) return
    setGeneratingPDF(true)
    setPDFError('')
    try {
      setPDFResult(await refreshPDFAccess(result.optimization_id))
    } catch (error) {
      if (error.response?.status === 401) setPDFError('Your session could not be verified. Log in again and retry.')
      else setPDFError('Secure PDF access is unavailable. Please try again.')
    } finally {
      setGeneratingPDF(false)
    }
  }

  if (pdfResult) {
    return (
      <>
        {pdfError && <div className="mt-6 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">{pdfError}</div>}
        <PDFPreview
          company={company}
          loading={generatingPDF}
          onBack={() => setPDFResult(null)}
          onRefresh={handleRefreshAccess}
          onRegenerate={handleGeneratePDF}
          pdf={pdfResult}
          role={role}
          scoreComparison={comparison}
        />
      </>
    )
  }

  return (
    <div className="mt-6">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8" aria-labelledby="optimized-preview-title">
        <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Approved changes applied</p>
        <h2 id="optimized-preview-title" className="mt-1 text-2xl font-black text-ink">Optimized Resume Preview</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">Structured text preview only. No PDF has been generated.</p>

        <div className="mt-6 grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
          <div className="rounded-xl bg-slate-50 p-5 text-center">
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Before</p>
            <p className="mt-2 text-3xl font-black text-ink">{comparison.before}%</p>
          </div>
          <span className="text-center text-2xl font-black text-slate-300" aria-hidden="true">→</span>
          <div className="rounded-xl bg-brand-50 p-5 text-center">
            <p className="text-xs font-bold uppercase tracking-wide text-brand-700">After</p>
            <p className="mt-2 text-3xl font-black text-ink">{comparison.after}%</p>
            <p className={`mt-1 text-sm font-bold ${changeStyle}`}>{changeLabel}</p>
          </div>
        </div>

        <p className="mt-5 text-xs leading-5 text-slate-500">The after score is recalculated by the deterministic matcher and may increase, stay unchanged, or decrease.</p>
        {pdfError && <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">{pdfError}</div>}
        <button
          className="mt-6 rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-brand-600/20 hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={generatingPDF}
          onClick={handleGeneratePDF}
          type="button"
        >
          {generatingPDF ? 'Generating your resume…' : 'Generate Final Resume'}
        </button>
      </section>
      <ParsedResume resume={result.optimized_resume} />
    </div>
  )
}

export default OptimizedResume
