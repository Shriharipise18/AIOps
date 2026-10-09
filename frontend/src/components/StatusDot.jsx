/**
 * StatusDot — animated dot indicator for service health status.
 */

const variants = {
  ok:      'dot-ok',
  error:   'dot-error',
  loading: 'dot-loading',
  degraded:'dot-degraded',
  disconnected: 'dot-disabled',
  disabled: 'dot-disabled',
}

export default function StatusDot({ status = 'loading' }) {
  return <span className={`dot ${variants[status] ?? 'dot-loading'}`} aria-hidden="true" />
}
