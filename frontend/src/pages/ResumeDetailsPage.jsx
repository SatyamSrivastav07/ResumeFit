import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import DashboardHeader from '../components/DashboardHeader.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import JobDescriptionForm from '../components/JobDescriptionForm.jsx'
import ParsedResume from '../components/ParsedResume.jsx'
import { getResume, parseResume, refreshResumePDFAccess } from '../services/resumeService.js'
import { getApiErrorMessage } from '../services/api.js'

function ResumeDetailsPage() {
  const { resumeId } = useParams(); const [resume, setResume] = useState(null); const [loading, setLoading] = useState(true); const [parsing, setParsing] = useState(false); const [accessing, setAccessing] = useState(false); const [pdfAccess, setPdfAccess] = useState(null); const [error, setError] = useState('')
  useEffect(() => { getResume(resumeId).then(setResume).catch((requestError) => setError(getApiErrorMessage(requestError, 'Resume was not found or is unavailable.'))).finally(() => setLoading(false)) }, [resumeId])
  async function handleParse() { setParsing(true); setError(''); try { const data = await parseResume(resumeId); setResume((current) => ({ ...current, status: 'parsed', parsed_resume: data.resume })) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to parse this resume.')) } finally { setParsing(false) } }
  async function accessSavedPDF() { setAccessing(true); setError(''); try { setPdfAccess(await refreshResumePDFAccess(resumeId)) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to access the saved PDF right now.')) } finally { setAccessing(false) } }
  return <div className="min-h-screen bg-slate-50"><DashboardHeader /><main className="mx-auto max-w-5xl px-6 py-12">{loading && <p>Loading resume...</p>}{error && <ErrorBanner message={error} />}{resume && <><div className="rounded-2xl border bg-white p-6"><p className="text-xs font-bold uppercase text-brand-700">Saved Resume</p><h1 className="mt-2 text-3xl font-black">{resume.filename}</h1><p className="mt-2 text-sm text-slate-600">This PDF is saved to your account and can be reused without uploading again.</p><div className="mt-5 flex flex-wrap gap-3"><button className="rounded-xl border border-brand-200 bg-brand-50 px-5 py-3 text-sm font-bold text-brand-800 disabled:opacity-60" disabled={accessing} onClick={accessSavedPDF} type="button">{accessing ? 'Restoring access…' : pdfAccess ? 'Refresh PDF Links' : 'Access Saved PDF'}</button>{pdfAccess && <><a className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white" href={pdfAccess.preview_url} rel="noreferrer" target="_blank">Preview PDF</a><a className="rounded-xl bg-ink px-5 py-3 text-sm font-bold text-white" href={pdfAccess.download_url}>Download PDF</a></>}{!resume.parsed_resume && <button className="rounded-xl bg-ink px-5 py-3 text-sm font-bold text-white disabled:opacity-60" disabled={parsing} onClick={handleParse} type="button">{parsing ? 'Analyzing resume…' : 'Parse Resume'}</button>}</div></div><ParsedResume resume={resume.parsed_resume} />{resume.parsed_resume && <JobDescriptionForm resume={resume.parsed_resume} resumeId={resume.resume_id} />}</>}</main></div>
}
export default ResumeDetailsPage
