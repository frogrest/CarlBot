import { useCallback, useEffect, useRef, useState } from 'react'
import {
  cancelLocalLlmModelDownload,
  downloadLocalLlmModel,
  listLocalLlmModels,
  removeLocalLlmModel,
  selectLocalLlmModel,
} from '../api'
import type { LocalLlmModel, LocalLlmModelCatalog, ModelDownloadProgress } from '../types'

export type ModelManagerProps = {
  /** Ask the parent to re-read `/api/llm/status` after the active model changes. */
  onRefreshStatus: () => void
}

function formatBytes(bytes: number | null | undefined): string {
  if (!bytes || bytes <= 0) return '—'
  const gb = bytes / 1024 ** 3
  if (gb >= 1) return `${gb.toFixed(1)} GB`
  return `${Math.max(1, Math.round(bytes / 1024 ** 2))} MB`
}

function progressFor(
  catalog: LocalLlmModelCatalog | null,
  model: LocalLlmModel,
): ModelDownloadProgress | null {
  return catalog?.download?.[model.id] ?? null
}

/**
 * Curated local-model chooser. It only ever acts on allow-listed catalog ids
 * (no arbitrary URLs), shows truthful download/selection state, and never
 * claims a model is ready — readiness comes from the runtime status badge.
 */
export function ModelManager({ onRefreshStatus }: ModelManagerProps) {
  const [catalog, setCatalog] = useState<LocalLlmModelCatalog | null>(null)
  const [loadError, setLoadError] = useState('')
  const [actionError, setActionError] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(true)
  const pollTimer = useRef<number | null>(null)

  const refresh = useCallback(async () => {
    try {
      const next = await listLocalLlmModels()
      setCatalog(next)
      setLoadError('')
    } catch (error) {
      setLoadError(error instanceof Error ? error.message : 'Model service unavailable')
    }
  }, [])

  useEffect(() => {
    // Defer the initial fetch by a tick, matching the workspace refresh pattern
    // in App.tsx (keeps the effect a plain external-system sync).
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
  }, [refresh])

  // Poll only while something is actually downloading/verifying.
  useEffect(() => {
    const active = catalog
      ? Object.values(catalog.download).some(
          (p) => p.state === 'downloading' || p.state === 'verifying',
        )
      : false
    if (!active) return
    pollTimer.current = window.setInterval(() => void refresh(), 1500)
    return () => {
      if (pollTimer.current !== null) window.clearInterval(pollTimer.current)
    }
  }, [catalog, refresh])

  async function run(modelId: string, action: () => Promise<LocalLlmModelCatalog>) {
    setBusyId(modelId)
    setActionError('')
    try {
      const next = await action()
      setCatalog(next)
      onRefreshStatus()
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Model action failed')
    } finally {
      setBusyId(null)
    }
  }

  const models = catalog?.models ?? []
  const activeModel = models.find((m) => m.is_selected)

  return (
    <section className={`model-manager ${isOpen ? 'model-manager-open' : ''}`} aria-label="Local AI model">
      <div className="model-manager-header">
        <div className="model-manager-heading">
          <h3>Local AI model</h3>
          <p>
            Download a compatible GGUF model to run inference locally — no API key.
            Files are stored on this machine only; you are responsible for each model's license.
          </p>
        </div>
        <button
          type="button"
          className="button button-outline button-small"
          onClick={() => setIsOpen((open) => !open)}
          aria-expanded={isOpen}
        >
          {isOpen ? 'Hide' : 'Choose model'}
        </button>
      </div>

      {isOpen && (
        <>
          <div className="model-manager-meta">
            <span>
              Active:{' '}
              {activeModel ? (
                <strong>{activeModel.display_name}</strong>
              ) : (
                <strong>none selected</strong>
              )}
            </span>
            {catalog && catalog.models_dir && (
              <span className="model-manager-dir" title={catalog.models_dir}>
                Folder: <code>{catalog.models_dir}</code>
              </span>
            )}
          </div>

          {loadError && (
            <p className="model-manager-error" role="alert">
              Could not load the model catalog: {loadError}
            </p>
          )}
          {actionError && (
            <p className="model-manager-error" role="alert">
              {actionError}
            </p>
          )}

          <div className="model-grid">
            {models.map((model) => {
              const progress = progressFor(catalog, model)
              const state = progress?.state ?? (model.installed ? 'completed' : 'idle')
              const downloading = state === 'downloading' || state === 'verifying'
              const percent = progress?.percent ?? (downloading ? 0 : null)
              const isBusy = busyId === model.id

              return (
                <article className={`model-card ${model.is_selected ? 'model-card-selected' : ''}`} key={model.id}>
                  <div className="model-card-title">
                    <strong>{model.display_name}</strong>
                    {model.recommended && <span className="model-badge model-badge-rec">Recommended</span>}
                    {model.is_selected && <span className="model-badge model-badge-active">Active</span>}
                  </div>

                  <div className="model-card-facts">
                    <span>{model.parameters}</span>
                    <span>{model.quantization}</span>
                    <span>{formatBytes(model.size_bytes)}</span>
                    <span>≥ {model.min_ram_gb} GB RAM</span>
                    <span>{Math.round(model.context_window / 1024)}K context</span>
                  </div>

                  <p className="model-card-summary">{model.summary}</p>

                  {downloading && (
                    <div className="model-progress" role="progressbar" aria-valuenow={percent ?? 0} aria-valuemin={0} aria-valuemax={100}>
                      <div className="model-progress-bar" style={{ width: `${percent ?? 0}%` }} />
                      <span className="model-progress-label">
                        {state === 'verifying' ? 'Verifying…' : `Downloading… ${percent ?? 0}%`}
                        {' · '}
                        {formatBytes(progress?.bytes_downloaded ?? 0)} / {formatBytes(progress?.total_bytes ?? model.size_bytes)}
                      </span>
                    </div>
                  )}

                  {state === 'error' && progress?.error && (
                    <p className="model-card-error" role="alert">{progress.error}</p>
                  )}

                  <div className="model-card-actions">
                    <span className="model-license" title={`License: ${model.license}`}>{model.license}</span>

                    {model.installed ? (
                      <div className="model-card-buttons">
                        {!model.is_selected && (
                          <button
                            type="button"
                            className="button button-primary button-small"
                            disabled={isBusy}
                            onClick={() => void run(model.id, () => selectLocalLlmModel(model.id))}
                          >
                            {isBusy ? 'Loading…' : 'Use this model'}
                          </button>
                        )}
                        <button
                          type="button"
                          className="button button-outline button-small"
                          disabled={isBusy}
                          onClick={() => void run(model.id, () => removeLocalLlmModel(model.id))}
                        >
                          Remove
                        </button>
                      </div>
                    ) : downloading ? (
                      <button
                        type="button"
                        className="button button-outline button-small"
                        disabled={isBusy}
                        onClick={() => void run(model.id, () => cancelLocalLlmModelDownload(model.id))}
                      >
                        Cancel
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="button button-primary button-small"
                        disabled={isBusy}
                        onClick={() => void run(model.id, () => downloadLocalLlmModel(model.id))}
                      >
                        {isBusy ? 'Starting…' : state === 'error' || state === 'cancelled' ? 'Retry download' : 'Download'}
                      </button>
                    )}
                  </div>
                </article>
              )
            })}
          </div>
        </>
      )}
    </section>
  )
}
