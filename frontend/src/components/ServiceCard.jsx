/**
 * ServiceCard — displays the status of a single service (Backend / DB / Redis).
 */
import StatusDot from './StatusDot'

const badgeClass = {
  ok:      'badge badge-ok',
  error:   'badge badge-error',
  loading: 'badge badge-loading',
  degraded:'badge badge-degraded',
  disconnected: 'badge badge-disabled',
  disabled: 'badge badge-disabled',
}

const labelMap = {
  ok:      'Connected',
  error:   'Needs attention',
  disconnected: 'Not connected',
  loading: 'Checking…',
  degraded:'Degraded',
  disabled: 'Disabled for local development',
}

export default function ServiceCard({ label, status = 'loading', latency, icon }) {
  const visualStatus = status === 'error' ? 'degraded' : status
  return (
    <div
      className="card glow-brand animate-slide-up"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        transition: 'border-color 0.3s',
      }}
    >
      {/* Left: icon + name */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div className="aws-service-icon">
          {icon}
        </div>
        <div>
          <p style={{
            fontSize: '0.9rem',
            color: 'var(--aws-muted)',
            fontWeight: 600,
            margin: 0,
          }}>
            {label}
          </p>
        </div>
      </div>

      {/* Right: badge + latency */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem' }}>
        <span className={badgeClass[visualStatus] ?? 'badge badge-loading'}>
          <StatusDot status={visualStatus} />
          {labelMap[status] ?? '…'}
        </span>
        {latency !== undefined && status === 'ok' && (
          <span style={{ fontSize: '0.7rem', color: 'var(--aws-muted)', fontFamily: 'monospace' }}>
            {latency} ms
          </span>
        )}
      </div>
    </div>
  )
}
