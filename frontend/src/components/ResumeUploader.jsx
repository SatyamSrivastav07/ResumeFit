import { useRef, useState } from 'react'

import { parseResume, uploadResume } from '../services/resumeService.js'
import JobDescriptionForm from './JobDescriptionForm.jsx'
import ParsedResume from './ParsedResume.jsx'

const MAX_FILE_SIZE = 5 * 1024 * 1024

function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function validatePdf(file) {
  if (!file) return 'Choose a PDF resume to upload.'
  if (!file.name.toLowerCase().endsWith('.pdf')) return 'The filename must end in .pdf.'
  if (file.type && file.type !== 'application/pdf') return 'Only PDF resume files are accepted.'
  if (file.size === 0) return 'The selected PDF is empty.'
  if (file.size > MAX_FILE_SIZE) return 'The PDF must be 5 MB or smaller.'
  return ''
}

function ResumeUploader() {
  const inputRef = useRef(null)
  const [file, setFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [parsing, setParsing] = useState(false)
  const [parseError, setParseError] = useState('')
  const [parsedResume, setParsedResume] = useState(null)

  function selectFile(nextFile) {
    const validationError = validatePdf(nextFile)
    setResult(null)
    setParsedResume(null)
    setParseError('')
    setProgress(null)

    if (validationError) {
      setFile(null)
      setError(validationError)
      if (inputRef.current) inputRef.current.value = ''
      return
    }

    setFile(nextFile)
    setError('')
  }

  function handleInputChange(event) {
    selectFile(event.target.files?.[0])
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragActive(false)
    if (!uploading) selectFile(event.dataTransfer.files?.[0])
  }

  function removeFile() {
    setFile(null)
    setError('')
    setResult(null)
    setParsedResume(null)
    setParseError('')
    setProgress(null)
    if (inputRef.current) inputRef.current.value = ''
  }

  async function handleUpload() {
    const validationError = validatePdf(file)
    if (validationError) {
      setError(validationError)
      return
    }

    setUploading(true)
    setError('')
    setResult(null)
    setProgress(null)

    try {
      const uploadResult = await uploadResume(file, setProgress)
      setResult(uploadResult)
    } catch (requestError) {
      const status = requestError.response?.status
      const detail = requestError.response?.data?.detail

      if (status === 401) {
        setError('Your session could not be verified. Log in again and retry the upload.')
      } else if (status === 413) {
        setError('The PDF must be 5 MB or smaller.')
      } else if (status === 400 && typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Unable to upload your resume right now. Please try again.')
      }
    } finally {
      setUploading(false)
    }
  }

  async function handleParse() {
    if (!result?.resume_id) return

    setParsing(true)
    setParseError('')
    setParsedResume(null)
    try {
      const parseResult = await parseResume(result.resume_id)
      setParsedResume(parseResult.resume)
    } catch (requestError) {
      const status = requestError.response?.status
      const detail = requestError.response?.data?.detail
      if (status === 401) {
        setParseError('Your session could not be verified. Log in again and retry.')
      } else if ([404, 422].includes(status) && typeof detail === 'string') {
        setParseError(detail)
      } else if (status === 503) {
        setParseError('Resume parsing is not configured or temporarily unavailable.')
      } else {
        setParseError('Unable to analyze this resume right now. Please try again.')
      }
    } finally {
      setParsing(false)
    }
  }

  return (
    <div>
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-card sm:p-8">
      <div className="flex items-start gap-4">
        <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-lg font-black text-brand-700" aria-hidden="true">
          ↑
        </span>
        <div>
          <h2 className="text-xl font-bold text-ink">Upload Your Resume</h2>
          <p className="mt-1 leading-7 text-slate-600">
            Upload your current resume to start tailoring it for a job opening.
          </p>
        </div>
      </div>

      <div
        className={`mt-7 rounded-2xl border-2 border-dashed p-7 text-center transition sm:p-10 ${
          dragActive ? 'border-brand-500 bg-brand-50' : 'border-slate-300 bg-slate-50'
        }`}
        onDragEnter={(event) => {
          event.preventDefault()
          if (!uploading) setDragActive(true)
        }}
        onDragLeave={(event) => {
          event.preventDefault()
          setDragActive(false)
        }}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <p className="font-bold text-ink">Drag and drop your PDF here</p>
        <p className="mt-2 text-sm text-slate-500">PDF only · Maximum 5 MB</p>
        <label
          className={`mt-5 inline-block rounded-xl border border-slate-300 bg-white px-5 py-2.5 text-sm font-bold text-slate-700 shadow-sm focus-within:ring-2 focus-within:ring-brand-500 focus-within:ring-offset-2 ${
            uploading ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-brand-500 hover:text-brand-700'
          }`}
        >
          Browse files
          <input
            ref={inputRef}
            accept="application/pdf,.pdf"
            className="sr-only"
            disabled={uploading}
            onChange={handleInputChange}
            type="file"
          />
        </label>
      </div>

      {file && (
        <div className="mt-5 flex flex-col gap-4 rounded-xl border border-slate-200 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <p className="truncate text-sm font-bold text-ink">{file.name}</p>
            <p className="mt-1 text-xs text-slate-500">{formatFileSize(file.size)} · PDF</p>
          </div>
          <button
            className="self-start rounded-lg px-3 py-2 text-sm font-bold text-slate-500 hover:bg-slate-100 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50 sm:self-auto"
            disabled={uploading}
            onClick={removeFile}
            type="button"
          >
            Remove
          </button>
        </div>
      )}

      {error && (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          <span className="font-bold">Upload failed. </span>{error}
        </div>
      )}

      {result && (
        <div className="mt-5 rounded-xl border border-brand-100 bg-brand-50 p-5 text-sm text-brand-900" role="status">
          <p className="font-bold">Resume uploaded successfully.</p>
          <dl className="mt-3 grid gap-2 sm:grid-cols-[7rem_1fr]">
            <dt className="font-semibold">Resume ID:</dt>
            <dd className="break-all">{result.resume_id}</dd>
            <dt className="font-semibold">File:</dt>
            <dd className="break-all">{result.filename}</dd>
            <dt className="font-semibold">Status:</dt>
            <dd className="capitalize">{result.status}</dd>
          </dl>
        </div>
      )}

      {parseError && (
        <div className="mt-5 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800" role="alert">
          <span className="font-bold">Analysis failed. </span>{parseError}
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <button
          className="rounded-xl bg-brand-600 px-5 py-3 text-sm font-bold text-white shadow-lg shadow-brand-600/20 hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={!file || uploading || Boolean(result)}
          onClick={handleUpload}
          type="button"
        >
          {uploading ? (progress === null ? 'Uploading…' : `Uploading ${progress}%`) : 'Upload Resume'}
        </button>
        {uploading && progress !== null && (
          <div className="h-2 w-36 overflow-hidden rounded-full bg-slate-200" aria-label={`Upload progress ${progress}%`}>
            <div className="h-full rounded-full bg-brand-600 transition-[width]" style={{ width: `${progress}%` }} />
          </div>
        )}
        {result && !parsedResume && (
          <button
            className="rounded-xl bg-ink px-5 py-3 text-sm font-bold text-white shadow-lg hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={parsing}
            onClick={handleParse}
            type="button"
          >
            {parsing ? 'Analyzing resume…' : 'Parse Resume'}
          </button>
        )}
      </div>
    </section>
    <ParsedResume resume={parsedResume} />
    {parsedResume && result?.resume_id && <JobDescriptionForm resume={parsedResume} resumeId={result.resume_id} />}
    </div>
  )
}

export default ResumeUploader
