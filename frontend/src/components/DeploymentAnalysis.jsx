import { useState, useEffect } from 'react'
import { getAnalysis, getFriendlyApiMessage } from '../api/api'

export default function DeploymentAnalysis({ projectId }) {
  const [analysis, setAnalysis] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAnalysis = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getAnalysis(projectId)
      setAnalysis(res.data)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'loading deployment analysis'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAnalysis()
  }, [projectId])

  if (loading) return <div className="card text-center text-slate-400">Running Deployment Analysis...</div>
  if (error) return <div className="card"><div className="aws-notice" role="status">{error}</div><button onClick={fetchAnalysis} className="aws-inline-button">Retry analysis</button></div>
  if (!analysis) return null

  const { security, cost, performance } = analysis

  return (
    <div className="card animate-slide-up" style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--aws-text)', margin: 0 }}>
          Deployment Analysis
        </h2>
        <button onClick={fetchAnalysis} style={{ background: 'transparent', border: 'none', color: 'var(--aws-link)', cursor: 'pointer', fontSize: '0.85rem' }}>
          ↻ Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '2rem' }}>
        
        {/* Security Report */}
        <div style={{ background: 'var(--aws-input-bg)', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid var(--aws-border)' }}>
          <h3 style={{ fontSize: '1rem', color: 'var(--aws-text)', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
            <span>Security</span>
            <span className="badge" style={{
              background: security.overall_status === 'Secure' ? '#f0f4f0' : '#f7f1f0',
              color: security.overall_status === 'Secure' ? 'var(--aws-success)' : 'var(--aws-error)'
            }}>{security.overall_status}</span>
          </h3>
          {security.findings.length === 0 ? (
            <p style={{ color: 'var(--aws-muted)', fontSize: '0.875rem' }}>Built-in configuration checks found no issues. A CVE scanner is not configured.</p>
          ) : (
            <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {security.findings.map((f, i) => (
                <li key={i} style={{ borderBottom: '1px solid var(--aws-border)', paddingBottom: '0.75rem' }}>
                  <div style={{ color: 'var(--aws-text)', fontSize: '0.875rem', fontWeight: 500 }}>{f.finding}</div>
                  <div style={{ color: 'var(--aws-muted)', fontSize: '0.75rem', marginTop: '0.25rem' }}>Resource: {f.resource}</div>
                  <div style={{ color: 'var(--aws-link)', fontSize: '0.75rem', marginTop: '0.25rem' }}>Remediation: {f.remediation}</div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Cost Estimation */}
        <div style={{ background: 'var(--aws-input-bg)', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid var(--aws-border)' }}>
          <h3 style={{ fontSize: '1rem', color: 'var(--aws-text)', marginBottom: '1rem', display: 'flex', justifyContent: 'space-between' }}>
            <span>Cost Estimation</span>
            <span className="badge">{cost.source} ({cost.region})</span>
          </h3>
          {cost.available ? (
            <>
              <div style={{ fontSize: '2rem', fontWeight: 700, color: 'var(--aws-success)', marginBottom: '1rem' }}>
                ${Number(cost.total_monthly_usd).toFixed(2)} <span style={{ fontSize: '0.875rem', color: 'var(--aws-muted)', fontWeight: 400 }}>/ month</span>
              </div>
              <p className="workflow-footnote">Approximation from configured resource sizes and stated pricing assumptions; actual cloud charges vary.</p>
            </>
          ) : (
            <p style={{ color: 'var(--aws-muted)', fontSize: '0.875rem', margin: '0 0 1rem' }}>
              Cost estimate unavailable for this provider.
            </p>
          )}
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {cost.breakdown.map((item, i) => (
              <li key={i} style={{ display: 'flex', justifyContent: 'space-between', color: 'var(--aws-muted)', fontSize: '0.875rem' }}>
                <span>{item.item}</span>
                <span>${item.monthly_cost.toFixed(2)}</span>
              </li>
            ))}
          </ul>
          <details className="workflow-footnote">
            <summary>Pricing assumptions</summary>
            <ul>{(cost.assumptions || []).map((assumption) => <li key={assumption}>{assumption}</li>)}</ul>
          </details>
        </div>

        {/* Performance Insights */}
        <div style={{ background: 'var(--aws-input-bg)', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid var(--aws-border)' }}>
          <h3 style={{ fontSize: '1rem', color: 'var(--aws-text)', marginBottom: '1rem' }}>
            Performance Insights
          </h3>
          <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {performance.insights.map((insight, i) => (
              <li key={i} style={{ borderBottom: '1px solid var(--aws-border)', paddingBottom: '0.75rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ color: 'var(--aws-text)', fontSize: '0.875rem', fontWeight: 500 }}>{insight.topic}</span>
                  <span className="badge" style={{
                    background: insight.status === 'Optimal' ? '#f0f4f0' : '#f6f3ed',
                    color: insight.status === 'Optimal' ? 'var(--aws-success)' : 'var(--aws-warning)'
                  }}>{insight.status}</span>
                </div>
                <div style={{ color: 'var(--aws-muted)', fontSize: '0.75rem', marginTop: '0.5rem' }}>{insight.message}</div>
              </li>
            ))}
          </ul>
        </div>

      </div>
    </div>
  )
}
