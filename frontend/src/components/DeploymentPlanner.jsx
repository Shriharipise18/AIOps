import { useEffect, useState } from 'react'
import { generateArtifacts, getFriendlyApiMessage } from '../api/api'

function requirementsFor(project) {
  const saved = project?.requirements || {}
  return {
    deployment_platform: saved.deployment_platform || 'Kubernetes',
    cloud_provider: saved.cloud_provider || 'AWS',
    replicas: saved.replicas ?? 2,
    cpu_limit: saved.cpu_limit || '500m',
    memory_limit: saved.memory_limit || '512Mi',
    autoscaling: saved.autoscaling ?? false,
    is_public: saved.is_public ?? true,
    container_port: saved.container_port ?? project?.profile?.port ?? 8080,
    include_database: saved.include_database ?? Boolean(project?.profile?.database),
    include_redis: saved.include_redis ?? Boolean(project?.profile?.redis),
  }
}

export default function DeploymentPlanner({ project, onGenerated, serviceAvailable = true }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [reqs, setReqs] = useState(() => requirementsFor(project))

  useEffect(() => {
    setReqs(requirementsFor(project))
    setError(null)
  }, [project?.id])

  if (!project) return null

  const handleChange = (e) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : e.target.value
    setReqs({ ...reqs, [e.target.name]: value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await generateArtifacts(project.id, {
        ...reqs,
        replicas: parseInt(reqs.replicas, 10),
        container_port: parseInt(reqs.container_port, 10),
        cpu_limit: reqs.cpu_limit.trim() || null,
        memory_limit: reqs.memory_limit.trim() || null,
      })
      onGenerated(res.data)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'generating infrastructure'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="card animate-slide-up" style={{ marginTop: '2rem' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--aws-text)', marginBottom: '1.5rem' }}>
        AI Deployment Planner
      </h2>

      {error && (
        <div className="aws-notice" role="status">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
        
        <div>
          <label className="aws-form-label" htmlFor="deployment-platform">Platform</label>
          <select id="deployment-platform" name="deployment_platform" value={reqs.deployment_platform} onChange={handleChange} className="aws-control" disabled={!serviceAvailable}>
            <option>Kubernetes</option>
            <option>Docker Compose</option>
          </select>
        </div>

        <div>
          <label className="aws-form-label" htmlFor="cloud-provider">Provider</label>
          <select id="cloud-provider" name="cloud_provider" value={reqs.cloud_provider} onChange={handleChange} className="aws-control" disabled={!serviceAvailable}>
            <option>AWS</option>
            <option>GCP</option>
            <option>Azure</option>
            <option>None (Local)</option>
          </select>
        </div>

        <div>
          <label className="aws-form-label" htmlFor="deployment-replicas">Replicas</label>
            <input id="deployment-replicas" type="number" min="1" max="100" required name="replicas" value={reqs.replicas} onChange={handleChange} className="aws-control" disabled={!serviceAvailable} />
        </div>

        <div>
          <label className="aws-form-label" htmlFor="container-port">Container Port</label>
          <input id="container-port" type="number" min="1" max="65535" required name="container_port" value={reqs.container_port} onChange={handleChange} className="aws-control" disabled={!serviceAvailable} />
        </div>

        <div>
          <label className="aws-form-label" htmlFor="cpu-limit">CPU Limit</label>
          <input id="cpu-limit" type="text" name="cpu_limit" value={reqs.cpu_limit} onChange={handleChange} className="aws-control" placeholder="500m or 1" disabled={!serviceAvailable} />
        </div>

        <div>
          <label className="aws-form-label" htmlFor="memory-limit">Memory Limit</label>
          <input id="memory-limit" type="text" name="memory_limit" value={reqs.memory_limit} onChange={handleChange} className="aws-control" placeholder="512Mi or 1Gi" disabled={!serviceAvailable} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', gridColumn: '1 / -1' }}>
          <label className="aws-checkbox-label">
            <input type="checkbox" name="autoscaling" checked={reqs.autoscaling} onChange={handleChange} disabled={!serviceAvailable} /> Enable Autoscaling
          </label>
          <label className="aws-checkbox-label">
            <input type="checkbox" name="is_public" checked={reqs.is_public} onChange={handleChange} disabled={!serviceAvailable} /> Expose Publicly (Ingress/LB)
          </label>
          <label className="aws-checkbox-label">
            <input type="checkbox" name="include_database" checked={reqs.include_database} onChange={handleChange} disabled={!serviceAvailable} /> Include managed database in the cost estimate
          </label>
          <label className="aws-checkbox-label">
            <input type="checkbox" name="include_redis" checked={reqs.include_redis} onChange={handleChange} disabled={!serviceAvailable} /> Include managed Redis in the cost estimate
          </label>
        </div>

        <div style={{ gridColumn: '1 / -1', marginTop: '1rem' }}>
          <button
            type="submit"
            disabled={loading || !serviceAvailable}
            style={{
              width: '100%',
              padding: '0.75rem',
              borderRadius: '3px',
              background: 'var(--aws-orange)',
              color: 'var(--aws-navy-deep)',
              fontWeight: 600,
              border: '1px solid var(--aws-orange-dark)',
              cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? 'Generating deployment artifacts…' : !serviceAvailable ? 'Database connection required' : project.requirements ? 'Save requirements and generate new revision' : 'Save requirements and generate'}
          </button>
        </div>
      </form>
    </div>
  )
}
