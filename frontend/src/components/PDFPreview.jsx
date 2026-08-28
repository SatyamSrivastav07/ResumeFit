import { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

function PDFPreview({ company, loading, onBack, onRefresh, onRegenerate, pdf, role, scoreComparison }) {
  const [numPages, setNumPages] = useState(0)
  const [failedPreviewUrl, setFailedPreviewUrl] = useState('')
  const [pageWidth, setPageWidth] = useState(760)
  const previewRef = useRef(null)

  useEffect(() => {
    const node = previewRef.current
    if (!node) return undefined
    const updateWidth = () => setPageWidth(Math.max(260, Math.min(760, node.clientWidth - 32)))
    updateWidth()
    const observer = new ResizeObserver(updateWidth)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  const previewError = failedPreviewUrl === pdf.preview_url

  return (
    <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-card sm:p-8" aria-labelledby="final-resume-title">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Your tailored resume is ready</p>
          <h2 id="final-resume-title" className="mt-1 text-2xl font-black text-ink">Final Resume</h2>
          <p className="mt-2 text-sm text-slate-600">{company} · {role}</p>
          <p className="mt-1 text-xs text-slate-500">Secure links expire in {Math.round(pdf.expires_in / 60)} minutes.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <a
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-brand-600/20 hover:bg-brand-700"
            href={pdf.download_url}
          >
            Download PDF
          </a>
          <button className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold text-ink hover:bg-slate-50 disabled:opacity-60" disabled={loading} onClick={onRefresh} type="button">
            Refresh Link
          </button>
          <button className="rounded-xl border border-slate-300 px-4 py-3 text-sm font-bold text-ink hover:bg-slate-50 disabled:opacity-60" disabled={loading} onClick={onRegenerate} type="button">
            {loading ? 'Generating…' : 'Regenerate'}
          </button>
          <button className="rounded-xl px-4 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50" onClick={onBack} type="button">Back to Optimizations</button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <p className="rounded-xl bg-slate-50 px-4 py-3 text-sm"><span className="font-bold">ResumeFit Match Before:</span> {scoreComparison.before}%</p>
        <p className="rounded-xl bg-brand-50 px-4 py-3 text-sm"><span className="font-bold">After:</span> {scoreComparison.after}%</p>
      </div>

      {previewError ? (
        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5 text-sm text-amber-900" role="alert">
          <p className="font-bold">Your secure PDF link may have expired.</p>
          <p className="mt-1">Refresh the link to restore the preview. This does not regenerate your PDF.</p>
          <button className="mt-4 rounded-lg bg-amber-900 px-4 py-2 font-bold text-white disabled:opacity-60" disabled={loading} onClick={onRefresh} type="button">Refresh Link</button>
        </div>
      ) : (
        <div ref={previewRef} className="mt-6 overflow-hidden rounded-xl border border-slate-200 bg-slate-200 p-4">
          <Document
            file={pdf.preview_url}
            key={pdf.preview_url}
            loading={<p className="py-12 text-center text-sm font-semibold text-slate-600">Loading secure PDF preview…</p>}
            onLoadError={() => setFailedPreviewUrl(pdf.preview_url)}
            onLoadSuccess={({ numPages: loadedPages }) => setNumPages(loadedPages)}
          >
            <div className="space-y-4">
              {Array.from({ length: numPages }, (_, index) => (
                <div className="mx-auto w-fit max-w-full overflow-hidden bg-white shadow-lg" key={`page-${index + 1}`}>
                  <Page pageNumber={index + 1} renderAnnotationLayer renderTextLayer width={pageWidth} />
                </div>
              ))}
            </div>
          </Document>
        </div>
      )}
    </section>
  )
}

export default PDFPreview
