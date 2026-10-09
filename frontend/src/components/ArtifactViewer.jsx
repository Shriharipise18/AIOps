import { useEffect, useState } from 'react'
import { downloadArtifactBundle, getFriendlyApiMessage } from '../api/api'

export default function ArtifactViewer({ generation, projectId }) {
  const [activeFile, setActiveFile] = useState(
    Object.keys(generation?.artifacts || {})[0] || null
  )
  const [downloadError, setDownloadError] = useState(null)
  const [downloading, setDownloading] = useState(false)

  useEffect(() => {
    setActiveFile(Object.keys(generation?.artifacts || {})[0] || null)
    setDownloadError(null)
  }, [generation?.id])

  if (!generation || !generation.artifacts) return null

  const files = Object.keys(generation.artifacts)

  const handleDownload = () => {
    if (!activeFile) return;
    const content = generation.artifacts[activeFile];
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = activeFile.replaceAll('/', '__').replaceAll('\\', '__');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  const handleDownloadAll = async () => {
    if (!projectId || !generation.id) return
    setDownloading(true)
    setDownloadError(null)
    try {
      const response = await downloadArtifactBundle(projectId, generation.id)
      const url = URL.createObjectURL(new Blob([response.data], { type: 'application/zip' }))
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `devops-artifacts-v${generation.artifact_version}.zip`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) {
      setDownloadError(getFriendlyApiMessage(err, 'downloading the artifact bundle'))
    } finally {
      setDownloading(false)
    }
  };

  return (
    <div className="card animate-slide-up" style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--aws-text)', margin: 0 }}>
          Generated DevOps Artifacts
        </h2>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button onClick={handleDownloadAll} disabled={downloading} style={{ padding: '0.25rem 0.75rem', background: 'var(--aws-panel-muted)', color: 'var(--aws-text)', border: '1px solid var(--aws-border)', borderRadius: '4px', cursor: downloading ? 'wait' : 'pointer', fontSize: '0.75rem' }}>
            {downloading ? 'Packaging…' : 'Download ZIP'}
          </button>
          <span className="badge badge-ok">v{generation.artifact_version}</span>
          <span className="badge" style={{ background: 'var(--aws-panel-muted)', color: 'var(--aws-muted)' }}>
            {generation.model_used}
          </span>
        </div>
      </div>

      {downloadError && <div className="aws-notice" role="alert" style={{ marginBottom: '0.75rem' }}>{downloadError}</div>}

      <div style={{ display: 'flex', border: '1px solid var(--aws-border)', borderRadius: '0.5rem', overflow: 'hidden' }}>
        
        {/* Sidebar */}
        <div style={{ width: '250px', background: 'var(--aws-panel-muted)', borderRight: '1px solid var(--aws-border)' }}>
          {files.map(filename => (
            <button
              key={filename}
              onClick={() => setActiveFile(filename)}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                padding: '0.75rem 1rem',
                fontSize: '0.875rem',
                background: activeFile === filename ? 'var(--aws-panel-muted)' : 'transparent',
                color: activeFile === filename ? 'var(--aws-link)' : 'var(--aws-muted)',
                border: 'none',
                borderBottom: '1px solid var(--aws-border)',
                cursor: 'pointer',
              }}
            >
              📄 {filename}
            </button>
          ))}
        </div>

        {/* Code View */}
        <div style={{ flex: 1, background: 'var(--aws-code-bg)', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '0.5rem 1rem', background: 'var(--aws-code-bg)', borderBottom: '1px solid var(--aws-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
             <span style={{ fontSize: '0.85rem', color: 'var(--aws-muted)' }}>{activeFile}</span>
             <button onClick={handleDownload} style={{ background: 'transparent', border: 'none', color: 'var(--aws-link)', cursor: 'pointer', fontSize: '0.75rem' }}>
               ↓ Download File
             </button>
          </div>
          <div style={{ padding: '1rem', overflowX: 'auto', flex: 1 }}>
            <pre style={{ margin: 0, fontSize: '0.85rem', color: 'var(--aws-text)', fontFamily: 'monospace' }}>
              <code>{generation.artifacts[activeFile]}</code>
            </pre>
          </div>
        </div>

      </div>
    </div>
  )
}
