import { useState, useEffect } from 'react'
import { getProjectStatus, runValidation, attemptRepair, getFriendlyApiMessage } from '../api/api'

export default function ValidationLoop({ projectId, onUpdateArtifacts, onStatusChange, serviceAvailable = true }) {
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchStatus = async () => {
    setHistoryLoading(true)
    try {
      const res = await getProjectStatus(projectId)
      const nextHistory = res.data.history || []
      setHistory(nextHistory)
      setError(null)
      onStatusChange?.(nextHistory.at(-1)?.validation_status ?? null)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'loading validation history'))
      onStatusChange?.(null)
    } finally {
      setHistoryLoading(false)
    }
  }

  useEffect(() => {
    setHistory([])
    setHistoryLoading(true)
    setError(null)
    onStatusChange?.(null)
    fetchStatus()
  }, [projectId])

  const handleValidate = async () => {
    setLoading(true)
    setError(null)
    try {
      await runValidation(projectId)
      await fetchStatus()
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'running validation'))
    } finally {
      setLoading(false)
    }
  }

  const handleRepair = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await attemptRepair(projectId)
      onUpdateArtifacts(res.data)
      await fetchStatus()
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'repairing the generated files'))
    } finally {
      setLoading(false)
    }
  }

  if (historyLoading) return <div className="card" role="status">Loading validation history…</div>
  if (!history.length) return (
    <div className="card">
      {error ? <div className="aws-notice" role="alert">{error}</div> : <p className="workflow-profile-empty">No generated revision is available to validate yet.</p>}
      <button type="button" onClick={fetchStatus} disabled={loading} className="aws-inline-button">Retry history</button>
    </div>
  )

  const latest = history[history.length - 1]
  const isPassed = latest.validation_status === 'passed'
  const isFailed = latest.validation_status === 'failed'
  const needsValidation = latest.validation_status === 'unvalidated'

  return (
    <div className="card animate-slide-up" style={{ marginTop: '2rem' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--aws-text)', marginBottom: '1.5rem' }}>
        AI Self-Correction Loop
      </h2>

      {error && (
        <div className="aws-notice" role="status">
          {error}
        </div>
      )}

      {/* Timeline */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
        {history.map((step, idx) => (
          <div key={step.generation_id} style={{ 
            padding: '1rem', 
            borderRadius: '0.5rem', 
            background: 'var(--aws-input-bg)', 
            border: '1px solid var(--aws-border)' 
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <strong style={{ color: 'var(--aws-text)' }}>
                {step.is_repair ? `Repair #${step.repair_attempt_num}` : `Generation #${step.version}`}
              </strong>
              <span className={`badge ${step.validation_status === 'passed' ? 'badge-ok' : step.validation_status === 'failed' ? 'badge-error' : 'badge-loading'}`}>
                {step.validation_status === 'passed' ? 'Passed' : 
                 step.validation_status === 'failed' ? 'Failed' : 'Pending validation'}
              </span>
            </div>
            
            {step.errors && step.errors.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: '1.5rem', color: 'var(--aws-error)', fontSize: '0.875rem' }}>
                {step.errors.map((err, i) => (
                  <li key={i}>{err.artifact ? `${err.artifact}: ` : ''}{err.message}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: '1rem' }}>
        {needsValidation && (
          <button
            onClick={handleValidate}
            disabled={loading || !serviceAvailable}
            style={{
              flex: 1, padding: '0.75rem', borderRadius: '0.5rem',
              background: 'var(--aws-link)', color: 'white', fontWeight: 600, border: 'none',
              cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Running Validation...' : 'Run Deterministic Validation'}
          </button>
        )}

        {isFailed && (
          <button
            onClick={handleRepair}
            disabled={loading || !serviceAvailable}
            style={{
              flex: 1, padding: '0.75rem', borderRadius: '0.5rem',
              background: 'var(--aws-orange)', color: 'var(--aws-navy-deep)', fontWeight: 600, border: '1px solid var(--aws-orange-dark)',
              cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1
            }}
          >
            {loading ? 'Attempting Repair...' : 'Trigger AI Repair Engine'}
          </button>
        )}

        {isPassed && (
          <div style={{ flex: 1, padding: '0.75rem', textAlign: 'center', background: '#f1f4f1', color: 'var(--aws-success)', borderRadius: '0.5rem', fontWeight: 600 }}>
            Infrastructure is valid and ready for deployment.
          </div>
        )}
      </div>
    </div>
  )
}
