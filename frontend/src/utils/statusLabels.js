export const STATUS_LABELS = {
  uploaded: 'Uploaded',
  parsed: 'Parsed',
  parse_failed: 'Parse Failed',
  analyzed: 'Job Analyzed',
  matched: 'Matched',
  optimization_started: 'Suggestions Ready',
  suggestions_generated: 'Suggestions Ready',
  applied: 'Optimized',
  completed: 'PDF Ready',
  generated: 'PDF Ready',
}

export function statusLabel(status) {
  return STATUS_LABELS[status] || status
}
