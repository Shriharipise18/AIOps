import { useState, useEffect } from 'react'
import { getReadiness, triggerDeployment, getDeployStatus, getDeploymentTarget, getFriendlyApiMessage } from '../api/api'

export default function DeploymentEngine({ projectId, supportsKubernetes = true, serviceAvailable = true, lastDeployment, onReadinessChange, onDeploymentChange, onTargetChange }) {
  const [readiness, setReadiness] = useState(null)
  const [deployment, setDeployment] = useState(null)
  const [target, setTarget] = useState(null)
  const [namespace, setNamespace] = useState('default')
  const [loading, setLoading] = useState(true)
  const [targetLoading, setTargetLoading] = useState(true)
  const [error, setError] = useState(null)
  const [deploying, setDeploying] = useState(false)

  const fetchReadiness = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getReadiness(projectId)
      setReadiness(res.data)
      onReadinessChange?.(res.data)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'loading deployment readiness'))
      setReadiness(null)
      onReadinessChange?.(null)
    } finally {
      setLoading(false)
    }
  }

  const fetchTarget = async () => {
    setTargetLoading(true)
    try {
      const res = await getDeploymentTarget()
      setTarget(res.data)
      onTargetChange?.(res.data)
    } catch {
      const unavailable = { available: false, context: null, message: 'The Kubernetes target could not be checked.' }
      setTarget(unavailable)
      onTargetChange?.(unavailable)
    } finally {
      setTargetLoading(false)
    }
  }

  const handleDeploy = async () => {
    if (!target?.available || !target.context || !readiness?.is_ready) return
    const confirmed = window.confirm(
      `Apply these generated resources to Kubernetes context "${target.context}" in namespace "${namespace}"? This will create or update cluster resources.`
    )
    if (!confirmed) return

    setDeploying(true)
    setError(null)
    try {
      const res = await triggerDeployment(projectId, { namespace, expected_context: target.context })
      setDeployment(res.data)
      onDeploymentChange?.(res.data)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'starting deployment'))
    } finally {
      setDeploying(false)
    }
  }

  const fetchStatus = async (namespaceOverride = namespace) => {
    try {
      const res = await getDeployStatus(projectId, namespaceOverride)
      setDeployment(res.data)
      onDeploymentChange?.(res.data)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'refreshing deployment status'))
    }
  }

  useEffect(() => {
    setDeployment(lastDeployment || null)
    setNamespace(lastDeployment?.namespace || 'default')
    fetchReadiness()
    if (supportsKubernetes) {
      fetchTarget()
      if (lastDeployment?.deployment_id) fetchStatus(lastDeployment.namespace || 'default')
    } else {
      const unavailable = { available: false, context: null, message: 'This project is configured for Docker Compose. Select Kubernetes to deploy to a cluster.' }
      setTarget(unavailable)
      setTargetLoading(false)
      onTargetChange?.(unavailable)
    }
  }, [projectId, supportsKubernetes, lastDeployment?.deployment_id])

  return (
    <div className="card animate-slide-up deployment-engine-card">
      <div className="deployment-engine-heading">
        <div>
          <h2>Deployment orchestration</h2>
          <p>{supportsKubernetes ? 'Readiness gate and active Kubernetes target' : 'Readiness gate and downloadable Docker Compose bundle'}</p>
        </div>
        {deployment && <button onClick={fetchStatus} className="aws-inline-button">Refresh live status</button>}
      </div>

      {error && <div className="aws-notice" role="status">{error}</div>}

      <div className="deployment-governance-grid">
        <section className="deployment-readiness-panel">
          <p className="workflow-panel-label">Readiness score</p>
          {loading ? <p className="workflow-profile-empty">Calculating readiness…</p> : readiness ? (
            <>
              <div className="deployment-score-row">
                <div className={`deployment-score ${readiness.is_ready ? 'is-ready' : 'needs-review'}`}>{readiness.score}</div>
                <div>
                  <strong>{readiness.is_ready ? 'Ready for deployment' : 'Review recommended'}</strong>
                  <p>{readiness.is_ready ? 'Validation and configured gates meet the current threshold.' : 'Resolve findings and pass validation to enable deployment.'}</p>
                </div>
              </div>
              <ul className="deployment-factor-list">
                {(readiness.factors || []).map((factor, index) => (
                  <li key={`${factor.factor}-${index}`}>
                    <span>{factor.factor}</span><span>{factor.impact > 0 ? `+${factor.impact}` : factor.impact}</span>
                    <small>{factor.reason}</small>
                  </li>
                ))}
              </ul>
            </>
          ) : <p className="workflow-profile-empty">Readiness is not available until artifacts are generated.</p>}
        </section>

        <section className="deployment-target-panel">
          <p className="workflow-panel-label">{supportsKubernetes ? 'Kubernetes target' : 'Docker Compose bundle'}</p>
          {targetLoading ? <p className="workflow-profile-empty">Checking cluster connection…</p> : target?.available ? (
            <>
              <div className="deployment-context-row"><span>Active context</span><code>{target.context}</code></div>
              <label className="aws-form-label" htmlFor="deploy-namespace">Namespace</label>
              <input id="deploy-namespace" className="aws-control" value={namespace} onChange={(event) => setNamespace(event.target.value)} pattern="[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?" />
              <p className="workflow-footnote">The context is checked again immediately before applying the resources.</p>
            </>
          ) : (
            <div className="workflow-placeholder deployment-target-offline">
              <strong>{supportsKubernetes ? 'Cluster not configured' : 'Local bundle ready'}</strong>
              <p>{supportsKubernetes ? target?.message || 'Install kubectl and configure a reachable context on the backend machine to deploy.' : 'Download the artifact ZIP and run docker compose from the application source directory. This server does not start Docker Compose for you.'}</p>
            </div>
          )}
          <button
            onClick={handleDeploy}
            disabled={!serviceAvailable || deploying || loading || targetLoading || !target?.available || !readiness?.is_ready || !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(namespace)}
            className="deployment-action-button"
          >
            {deploying ? 'Applying resources…' : !serviceAvailable ? 'Database connection required' : !supportsKubernetes ? 'Kubernetes apply not selected' : target?.available ? 'Apply to Kubernetes' : 'Kubernetes target unavailable'}
          </button>
        </section>
      </div>

      {deployment && (
        <div className="deployment-live-result" role="status">
          <div className="deployment-live-heading">
            <strong>{deployment.status === 'success' ? 'Resources applied' : `Cluster status: ${deployment.status}`}</strong>
            {deployment.context && <code>{deployment.context} / {deployment.namespace}</code>}
          </div>
          <p>{deployment.message || 'Live deployment status loaded.'}</p>
          {deployment.details && <pre>{deployment.details}</pre>}
          {deployment.pods?.length > 0 && (
            <ul>{deployment.pods.map((pod) => <li key={pod.name}><code>{pod.name}</code><span>{pod.status}</span></li>)}</ul>
          )}
          {deployment.services?.length > 0 && (
            <ul>{deployment.services.map((service) => <li key={service.name}><code>{service.name}</code><span>{service.cluster_ip} · {service.ports}</span></li>)}</ul>
          )}
        </div>
      )}
    </div>
  )
}
