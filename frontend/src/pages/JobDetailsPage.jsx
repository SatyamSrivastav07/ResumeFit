import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import DashboardHeader from '../components/DashboardHeader.jsx'
import ErrorBanner from '../components/ErrorBanner.jsx'
import JobAnalysis from '../components/JobAnalysis.jsx'
import MatchAnalysis from '../components/MatchAnalysis.jsx'
import { analyzeMatch, getJob } from '../services/jobService.js'
import { generateOptimizations } from '../services/optimizationService.js'
import { getApiErrorMessage } from '../services/api.js'

function JobDetailsPage() {
  const { jobId } = useParams(); const [job, setJob] = useState(null); const [loading, setLoading] = useState(true); const [working, setWorking] = useState(false); const [optimization, setOptimization] = useState(null); const [error, setError] = useState('')
  useEffect(() => { getJob(jobId).then(setJob).catch((requestError) => setError(getApiErrorMessage(requestError, 'Job was not found or is unavailable.'))).finally(() => setLoading(false)) }, [jobId])
  async function match() { setWorking(true); setError(''); try { const data = await analyzeMatch(jobId); setJob((current) => ({ ...current, status: 'matched', match_analysis: data.match })) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to calculate resume match.')) } finally { setWorking(false) } }
  async function optimize() { setWorking(true); setError(''); try { setOptimization(await generateOptimizations({ job_id: jobId })) } catch (requestError) { setError(getApiErrorMessage(requestError, 'Unable to generate optimization suggestions.')) } finally { setWorking(false) } }
  return <div className="min-h-screen bg-slate-50"><DashboardHeader /><main className="mx-auto max-w-5xl px-6 py-12">{loading && <p>Loading job...</p>}{error && <ErrorBanner message={error} />}{job && <><h1 className="text-3xl font-black">{job.role}</h1><p className="mt-2 text-slate-600">{job.company}</p><JobAnalysis result={{ analysis: job.analysis }} /><MatchAnalysis result={job.match_analysis ? { match: job.match_analysis } : null} />{!job.match_analysis && <button className="mt-6 rounded-xl bg-ink px-5 py-3 font-bold text-white disabled:opacity-60" disabled={working} onClick={match}>{working ? 'Calculating match…' : 'Calculate Resume Match'}</button>}{job.match_analysis && !optimization && <button className="mt-6 rounded-xl bg-brand-600 px-5 py-3 font-bold text-white disabled:opacity-60" disabled={working} onClick={optimize}>{working ? 'Generating suggestions…' : 'Optimize Resume'}</button>}{optimization && <Link className="mt-6 inline-block rounded-xl bg-brand-600 px-5 py-3 font-bold text-white" to={`/optimizations/${optimization.optimization_id}`}>Continue Optimization</Link>}</>}</main></div>
}
export default JobDetailsPage
