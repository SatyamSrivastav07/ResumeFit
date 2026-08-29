import { useState } from 'react'

import { analyzeJob, analyzeMatch } from '../services/jobService.js'
import { applyOptimizations, generateOptimizations } from '../services/optimizationService.js'
import ErrorBanner from './ErrorBanner.jsx'
import JobAnalysis from './JobAnalysis.jsx'
import MatchAnalysis from './MatchAnalysis.jsx'
import OptimizationSuggestions from './OptimizationSuggestions.jsx'
import OptimizedResume from './OptimizedResume.jsx'

const MAX_JOB_DESCRIPTION = 30000
const MIN_JOB_DESCRIPTION = 100

function validate(values) {
  const errors = {}
  const company = values.company.trim()
  const role = values.role.trim()
  const jobDescription = values.jobDescription.trim()

  if (!company) errors.company = 'Company name is required.'
  else if (company.length > 150) errors.company = 'Company name must be 150 characters or fewer.'

  if (!role) errors.role = 'Job role is required.'
  else if (role.length > 150) errors.role = 'Job role must be 150 characters or fewer.'

  if (!jobDescription) errors.jobDescription = 'Job description is required.'
  else if (jobDescription.length < MIN_JOB_DESCRIPTION) errors.jobDescription = `Enter at least ${MIN_JOB_DESCRIPTION} meaningful characters.`
  else if (jobDescription.length > MAX_JOB_DESCRIPTION) errors.jobDescription = `Job description must be ${MAX_JOB_DESCRIPTION.toLocaleString()} characters or fewer.`

  return errors
}

function JobDescriptionForm({ resumeId }) {
  const [values, setValues] = useState({ company: '', role: '', jobDescription: '' })
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [requestError, setRequestError] = useState('')
  const [result, setResult] = useState(null)
  const [matching, setMatching] = useState(false)
  const [matchError, setMatchError] = useState('')
  const [matchResult, setMatchResult] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [optimizationError, setOptimizationError] = useState('')
  const [optimization, setOptimization] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState('')
  const [invalidSuggestionIds, setInvalidSuggestionIds] = useState([])
  const [appliedResult, setAppliedResult] = useState(null)

  function updateField(field, value) {
    setValues((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: '' }))
    setRequestError('')
    setResult(null)
    setMatchResult(null)
    setMatchError('')
    setOptimization(null)
    setSuggestions([])
    setAppliedResult(null)
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return

    const validationErrors = validate(values)
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length) return

    setSubmitting(true)
    setRequestError('')
    setResult(null)
    setMatchResult(null)
    setMatchError('')
    setOptimization(null)
    setSuggestions([])
    setAppliedResult(null)

    try {
      const analysisResult = await analyzeJob({
        resume_id: resumeId,
        company: values.company.trim(),
        role: values.role.trim(),
        job_description: values.jobDescription.trim(),
      })
      setResult(analysisResult)
    } catch (error) {
      const status = error.response?.status
      if (status === 401) {
        setRequestError('Your session could not be verified. Log in again and retry.')
      } else if (status === 422) {
        setRequestError('Please enter valid company, role, and job description details.')
      } else if ([502, 503].includes(status)) {
        setRequestError('Job analysis is temporarily unavailable. Please try again.')
      } else {
        setRequestError('Job analysis failed. Please try again.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function handleMatch() {
    if (!result?.job_id || !result?.analysis || matching) return
    setMatching(true)
    setMatchError('')
    setMatchResult(null)
    try {
      const nextMatch = await analyzeMatch(result.job_id)
      setMatchResult(nextMatch)
    } catch (error) {
      const status = error.response?.status
      if (status === 401) {
        setMatchError('Your session could not be verified. Log in again and retry.')
      } else if (status === 422) {
        setMatchError('The parsed resume or job analysis is invalid. Please run the workflow again.')
      } else {
        setMatchError('Resume match analysis failed. Please try again.')
      }
    } finally {
      setMatching(false)
    }
  }

  async function handleGenerateOptimizations() {
    if (!matchResult?.match || !result?.analysis || generating) return
    setGenerating(true)
    setOptimizationError('')
    setOptimization(null)
    setSuggestions([])
    setAppliedResult(null)
    try {
      const response = await generateOptimizations({ job_id: result.job_id })
      setOptimization(response)
      setSuggestions(response.suggestions)
    } catch (error) {
      const status = error.response?.status
      if (status === 401) setOptimizationError('Your session could not be verified. Log in again and retry.')
      else if (status === 422) setOptimizationError('The resume optimization request is invalid. Please run the workflow again.')
      else if ([502, 503].includes(status)) setOptimizationError('Safe AI suggestions are temporarily unavailable. Please try again.')
      else setOptimizationError('Unable to generate resume suggestions right now.')
    } finally {
      setGenerating(false)
    }
  }

  function updateSuggestion(id, changes) {
    setSuggestions((current) => current.map((item) => item.id === id ? { ...item, ...changes } : item))
    setInvalidSuggestionIds((current) => current.filter((item) => item !== id))
    setApplyError('')
    setAppliedResult(null)
  }

  async function handleApplyOptimizations() {
    if (!optimization?.optimization_id || applying) return
    setApplying(true)
    setApplyError('')
    setInvalidSuggestionIds([])
    setAppliedResult(null)
    try {
      const response = await applyOptimizations(optimization.optimization_id, suggestions)
      setAppliedResult(response)
    } catch (error) {
      const detail = error.response?.data?.detail
      if (error.response?.status === 422 && detail?.invalid_suggestion_ids) {
        setInvalidSuggestionIds(detail.invalid_suggestion_ids)
        setApplyError('This edit introduces information that could not be verified from your original resume.')
      } else if (error.response?.status === 401) {
        setApplyError('Your session could not be verified. Log in again and retry.')
      } else {
        setApplyError('Unable to apply the approved changes right now. Please try again.')
      }
    } finally {
      setApplying(false)
    }
  }

  return (
    <>
      <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8" aria-labelledby="job-form-title">
        <div className="flex items-start gap-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 font-black text-brand-700" aria-hidden="true">3</span>
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.16em] text-brand-700">Next step</p>
            <h2 id="job-form-title" className="mt-1 text-2xl font-black text-ink">Tailor for a Job</h2>
            <p className="mt-1 leading-7 text-slate-600">Enter the posting details for independent requirement analysis.</p>
          </div>
        </div>

        <form className="mt-7 space-y-5" noValidate onSubmit={handleSubmit}>
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="block text-sm font-bold text-slate-700">
              Company Name
              <input
                aria-describedby={errors.company ? 'company-error' : undefined}
                aria-invalid={Boolean(errors.company)}
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 font-normal text-ink placeholder:text-slate-400 focus:border-brand-500"
                maxLength={150}
                onChange={(event) => updateField('company', event.target.value)}
                placeholder="Google"
                value={values.company}
              />
              {errors.company && <span id="company-error" className="mt-2 block text-xs font-semibold text-red-700">{errors.company}</span>}
            </label>

            <label className="block text-sm font-bold text-slate-700">
              Job Role
              <input
                aria-describedby={errors.role ? 'role-error' : undefined}
                aria-invalid={Boolean(errors.role)}
                className="mt-2 w-full rounded-xl border border-slate-300 px-4 py-3 font-normal text-ink placeholder:text-slate-400 focus:border-brand-500"
                maxLength={150}
                onChange={(event) => updateField('role', event.target.value)}
                placeholder="Software Engineer"
                value={values.role}
              />
              {errors.role && <span id="role-error" className="mt-2 block text-xs font-semibold text-red-700">{errors.role}</span>}
            </label>
          </div>

          <label className="block text-sm font-bold text-slate-700">
            Job Description
            <textarea
              aria-describedby={errors.jobDescription ? 'job-description-error job-description-count' : 'job-description-count'}
              aria-invalid={Boolean(errors.jobDescription)}
              className="mt-2 min-h-64 w-full resize-y rounded-xl border border-slate-300 px-4 py-3 font-normal leading-6 text-ink placeholder:text-slate-400 focus:border-brand-500"
              maxLength={MAX_JOB_DESCRIPTION}
              onChange={(event) => updateField('jobDescription', event.target.value)}
              placeholder="Paste the complete job posting here…"
              value={values.jobDescription}
            />
            <span className="mt-2 flex items-start justify-between gap-4">
              <span id="job-description-error" className="text-xs font-semibold text-red-700">{errors.jobDescription}</span>
              <span id="job-description-count" className="ml-auto shrink-0 text-xs font-medium text-slate-500">
                {values.jobDescription.length.toLocaleString()} / {MAX_JOB_DESCRIPTION.toLocaleString()}
              </span>
            </span>
          </label>

          {requestError && <ErrorBanner message={requestError} />}

          <button
            className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-brand-600/20 hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={submitting}
            type="submit"
          >
            {submitting ? 'Analyzing job description…' : 'Analyze Job'}
          </button>
        </form>
      </section>

      <JobAnalysis result={result} />
      {result && !matchResult && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
          <h2 className="text-xl font-black text-ink">Ready to compare</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Calculate a deterministic match from the parsed resume and structured job requirements.</p>
          {matchError && <div className="mt-4"><ErrorBanner message={matchError} /></div>}
          <button
            className="mt-5 rounded-xl bg-ink px-5 py-3 text-sm font-bold text-white shadow-lg hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={matching}
            onClick={handleMatch}
            type="button"
          >
            {matching ? 'Analyzing resume match…' : 'Calculate Resume Match'}
          </button>
        </section>
      )}
      <MatchAnalysis result={matchResult} />
      {matchResult && !optimization && (
        <section className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
          <h2 className="text-xl font-black text-ink">Improve relevant wording safely</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600">Generate targeted rewrites grounded only in information already present in your resume.</p>
          {optimizationError && <div className="mt-4"><ErrorBanner message={optimizationError} /></div>}
          <button
            className="mt-5 rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-brand-600/20 hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={generating}
            onClick={handleGenerateOptimizations}
            type="button"
          >
            {generating ? 'Generating targeted suggestions…' : 'Optimize Resume'}
          </button>
        </section>
      )}
      {optimization && (
        <OptimizationSuggestions
          applying={applying}
          error={applyError}
          invalidIds={invalidSuggestionIds}
          onApply={handleApplyOptimizations}
          onChange={updateSuggestion}
          suggestions={suggestions}
        />
      )}
      <OptimizedResume
        company={result?.analysis?.company || values.company.trim()}
        jobId={result?.job_id}
        key={appliedResult?.optimization_id || 'no-applied-optimization'}
        result={appliedResult}
        resumeId={resumeId}
        role={result?.analysis?.role || values.role.trim()}
      />
    </>
  )
}

export default JobDescriptionForm
