import { useState, useRef } from 'react'
import { analyzeGithub, analyzeZip, getFriendlyApiMessage } from '../api/api'

export default function RepoAnalyzer({ onAnalyzed, onAttemptCompleted, serviceAvailable = true }) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  
  const fileInputRef = useRef(null)

  const handleGithubSubmit = async (e) => {
    e.preventDefault()
    if (!url) return

    setLoading(true)
    setError(null)
    try {
      const res = await analyzeGithub(url)
      onAnalyzed(res.data)
      setUrl('')
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'analyzing this repository'))
    } finally {
      setLoading(false)
      onAttemptCompleted?.()
    }
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Choose a .zip archive.')
      e.target.value = ''
      return
    }
    if (file.size > 100 * 1024 * 1024) {
      setError('This archive is larger than the 100 MB upload limit.')
      e.target.value = ''
      return
    }

    setLoading(true)
    setError(null)
    try {
      const res = await analyzeZip(file)
      onAnalyzed(res.data)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'analyzing this archive'))
    } finally {
      setLoading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      onAttemptCompleted?.()
    }
  }

  return (
    <div className="card" style={{ marginBottom: '2rem' }}>
      <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--aws-text)', marginBottom: '1.5rem' }}>
        Analyze Repository
      </h2>

      {!serviceAvailable && (
        <div className="aws-notice" role="status">
          Connect the local API to enable repository analysis.
        </div>
      )}

      {error && (
        <div className="aws-notice" role="status">
          {error}
        </div>
      )}

      <div className="aws-analyzer-fields">
        {/* GitHub URL Form */}
        <form onSubmit={handleGithubSubmit} className="aws-analyzer-field">
            <label htmlFor="github-repository-url" style={{ display: 'block', fontSize: '0.875rem', color: 'var(--aws-text)', marginBottom: '0.5rem' }}>
              GitHub URL
            </label>
          <div className="aws-repo-form-row">
            <input
              id="github-repository-url"
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              disabled={loading || !serviceAvailable}
              style={{
                flex: 1,
                padding: '0.75rem',
                borderRadius: '0.5rem',
                background: 'var(--aws-input-bg)',
                border: '1px solid var(--aws-border)',
                color: 'var(--aws-text)',
                outline: 'none',
              }}
            />
            <button
              type="submit"
              disabled={loading || !url || !serviceAvailable}
              style={{
                padding: '0 1.5rem',
                borderRadius: '0.5rem',
                background: 'var(--aws-orange)',
                color: 'var(--aws-navy-deep)',
                fontWeight: 500,
                border: '1px solid var(--aws-orange-dark)',
              cursor: (loading || !url || !serviceAvailable) ? 'not-allowed' : 'pointer',
              opacity: (loading || !url || !serviceAvailable) ? 0.6 : 1,
              }}
            >
              {loading ? 'Downloading and analyzing…' : serviceAvailable ? 'Analyze repository' : 'Connect API'}
            </button>
          </div>
        </form>

        {/* ZIP Upload Form */}
        <div className="aws-analyzer-field">
          <label htmlFor="repository-zip-upload" style={{ display: 'block', fontSize: '0.875rem', color: 'var(--aws-text)', marginBottom: '0.5rem' }}>
            Upload ZIP Archive
          </label>
          <input
            type="file"
            id="repository-zip-upload"
            accept=".zip"
            ref={fileInputRef}
            onChange={handleFileUpload}
            disabled={loading || !serviceAvailable}
            className="aws-file-input"
            style={{
              display: 'block',
              width: '100%',
              padding: '0.65rem',
              borderRadius: '0.5rem',
              background: 'var(--aws-input-bg)',
              border: '1px dashed var(--aws-muted)',
              color: 'var(--aws-muted)',
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          />
        </div>
      </div>
    </div>
  )
}
