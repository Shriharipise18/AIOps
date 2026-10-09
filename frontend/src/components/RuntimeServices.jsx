import { useState } from 'react'
import StatusDot from './StatusDot'

const SERVICES = [
  { id: 'backend', label: 'Backend API', icon: 'API' },
  { id: 'mongodb', label: 'MongoDB', icon: 'MDB' },
  { id: 'redis', label: 'Redis', icon: 'KV' },
  { id: 'ai', label: 'Groq AI', icon: 'AI' },
]

const STATUS_LABELS = {
  ok: 'Connected',
  loading: 'Checking',
  disconnected: 'Not connected',
  error: 'Unavailable',
  disabled: 'Disabled locally',
  configured: 'Key configured',
  not_configured: 'Key required',
  degraded: 'Degraded',
}

function Detail({ label, children }) {
  return (
    <div className="runtime-service-detail">
      <span>{label}</span>
      <div>{children}</div>
    </div>
  )
}

export default function RuntimeServices({
  backendStatus,
  mongoStatus,
  mongoLatency,
  redisStatus,
  redisLatency,
  aiStatus,
  aiProvider,
  aiModel,
  aiKeyName,
  version,
  environment,
  apiBaseUrl,
}) {
  const [selected, setSelected] = useState('backend')
  const activeService = SERVICES.find((service) => service.id === selected)
  const statuses = { backend: backendStatus, mongodb: mongoStatus, redis: redisStatus, ai: aiStatus }
  const status = statuses[selected]
  const docsUrl = apiBaseUrl.replace(/\/api\/v1\/?$/, '/docs')
  const handleTabKeyDown = (event, index) => {
    let nextIndex = index
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % SERVICES.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + SERVICES.length) % SERVICES.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = SERVICES.length - 1
    else return

    event.preventDefault()
    const nextService = SERVICES[nextIndex]
    setSelected(nextService.id)
    document.getElementById(`runtime-tab-${nextService.id}`)?.focus()
  }

  return (
    <section id="services" className="runtime-services-section">
      <div className="runtime-services-heading">
        <div>
          <p className="aws-eyebrow">Service health</p>
          <h2>Runtime services</h2>
          <p>Choose a service to view its connection status and role in the workflow.</p>
        </div>
        <span className="runtime-services-summary">{SERVICES.length} services</span>
      </div>

      <div className="runtime-service-tabs" role="tablist" aria-label="Runtime services">
        {SERVICES.map((service, index) => (
          <button
            key={service.id}
            id={`runtime-tab-${service.id}`}
            type="button"
            role="tab"
            aria-selected={selected === service.id}
            aria-controls="runtime-service-panel"
            tabIndex={selected === service.id ? 0 : -1}
            className={`runtime-service-tab${selected === service.id ? ' is-active' : ''}`}
            onClick={() => setSelected(service.id)}
            onKeyDown={(event) => handleTabKeyDown(event, index)}
          >
            <span className="aws-service-icon">{service.icon}</span>
            <span>{service.label}</span>
            <span className={`runtime-tab-indicator is-${statuses[service.id] === 'ok' || statuses[service.id] === 'configured' ? 'ok' : statuses[service.id] === 'disabled' || statuses[service.id] === 'not_configured' ? 'disabled' : statuses[service.id] === 'loading' ? 'loading' : 'offline'}`} />
          </button>
        ))}
      </div>

      <div
        id="runtime-service-panel"
        className="card runtime-service-panel"
        role="tabpanel"
        aria-labelledby={`runtime-tab-${activeService.id}`}
        tabIndex="0"
      >
        <div className="runtime-service-panel-heading">
          <div className="runtime-service-title">
            <span className="runtime-service-mark">{activeService.icon}</span>
            <div>
              <h3>{activeService.label}</h3>
              <p>{selected === 'backend' ? 'FastAPI application service' : selected === 'mongodb' ? 'Primary persistent document database' : selected === 'redis' ? 'Optional cache and work queue' : 'AI provider for artifact generation and repair'}</p>
            </div>
          </div>
          <span className={`badge ${status === 'ok' || status === 'configured' ? 'badge-ok' : status === 'disabled' || status === 'not_configured' || status === 'loading' ? 'badge-disabled' : 'badge-degraded'}`}>
            <StatusDot status={status === 'error' ? 'degraded' : status === 'configured' ? 'ok' : status === 'not_configured' ? 'disabled' : status} />
            {STATUS_LABELS[status] || 'Status unavailable'}
          </span>
        </div>

        <div className="runtime-service-details">
          {selected === 'backend' && (
            <>
              <Detail label="API endpoint"><code>{apiBaseUrl}</code></Detail>
              <Detail label="Version"><span>{version || '—'}</span></Detail>
              <Detail label="Environment"><span>{environment || '—'}</span></Detail>
              <Detail label="API reference"><a href={docsUrl} target="_blank" rel="noreferrer">Open API docs</a></Detail>
            </>
          )}
          {selected === 'mongodb' && (
            <>
              <Detail label="Connection"><span>{mongoStatus === 'ok' ? 'MongoDB is responding to health checks.' : 'Connection status is reported by the backend.'}</span></Detail>
              <Detail label="Stored data"><span>Projects, repository profiles, and deployment specifications</span></Detail>
              <Detail label="Workflow history"><span>Generated artifacts, validation runs, and repair attempts</span></Detail>
              <Detail label="Health check latency"><span>{mongoStatus === 'ok' && mongoLatency !== undefined ? `${mongoLatency} ms` : '—'}</span></Detail>
            </>
          )}
          {selected === 'redis' && (
            <>
              <Detail label="Purpose"><span>Optional cache and background-work queue</span></Detail>
              <Detail label="Configuration"><span>{redisStatus === 'disabled' ? 'Disabled for local development' : 'Enabled in the backend configuration'}</span></Detail>
              <Detail label="Workflow impact"><span>{redisStatus === 'disabled' ? 'Repository analysis, artifact generation, and validation continue without Redis.' : 'Redis availability is reported by the backend health check.'}</span></Detail>
              <Detail label="Health check latency"><span>{redisStatus === 'ok' && redisLatency !== undefined ? `${redisLatency} ms` : '—'}</span></Detail>
            </>
          )}
          {selected === 'ai' && (
            <>
              <Detail label="Provider"><span>{aiProvider || 'Groq'}</span></Detail>
              <Detail label="Model"><code>{aiModel || 'openai/gpt-oss-120b'}</code></Detail>
              <Detail label="API key"><span>{aiStatus === 'configured' ? 'Present in backend configuration' : `Add ${aiKeyName || 'GROQ_API_KEY'} to backend/.env, then restart the backend`}</span></Detail>
              <Detail label="Used for"><span>Infrastructure artifact generation and validation repair</span></Detail>
              <Detail label="Connection check"><span>Key presence is shown here. A successful generation confirms the remote API is reachable.</span></Detail>
            </>
          )}
        </div>
      </div>
    </section>
  )
}
