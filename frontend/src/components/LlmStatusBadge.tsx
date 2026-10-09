import type { LocalLlmStatus } from '../types'

export type LlmStatusBadgeProps = {
  status: LocalLlmStatus | null
  onRetry?: () => void
  isRetrying?: boolean
  compact?: boolean
}

const STATE_LABELS: Record<LocalLlmStatus['state'], string> = {
  disabled: 'Local inference off',
  runtime_missing: 'Runtime missing',
  model_not_configured: 'Model not configured',
  loading: 'Loading model',
  ready: 'Local model ready',
  busy: 'Local model busy',
  error: 'Runtime error',
}

// Retry is only meaningful while the model is not usable and not intentionally off.
const RETRYABLE_STATES: LocalLlmStatus['state'][] = [
  'runtime_missing',
  'model_not_configured',
  'loading',
  'error',
]

/**
 * Truthful local-inference indicator. It never reports "ready" unless the
 * backend confirmed the model loaded (the status comes from GET /api/llm/status).
 */
export function LlmStatusBadge({ status, onRetry, isRetrying, compact = false }: LlmStatusBadgeProps) {
  if (!status) {
    return (
      <span className="llm-status llm-status-unknown" role="status">
        <span className="llm-status-dot" />
        Local inference status unavailable
      </span>
    )
  }

  const label = STATE_LABELS[status.state] ?? status.state
  const retryable = RETRYABLE_STATES.includes(status.state)

  return (
    <div
      className={`llm-status llm-status-${status.state}${compact ? ' llm-status-compact' : ''}`}
      role="status"
      aria-live="polite"
    >
      <span className="llm-status-dot" />
      <span className="llm-status-label">{label}</span>
      {!compact && status.detail && <span className="llm-status-detail">{status.detail}</span>}
      <span className="llm-status-local">Local inference · no API key</span>
      {retryable && onRetry && (
        <button
          type="button"
          className="button button-outline button-small llm-status-retry"
          onClick={onRetry}
          disabled={isRetrying}
        >
          {isRetrying ? 'Retrying…' : 'Retry initialization'}
        </button>
      )}
      {!compact && retryable && status.instructions.length > 0 && (
        <ul className="llm-status-instructions">
          {status.instructions.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      )}
    </div>
  )
}
