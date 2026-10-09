import { useEffect, useState } from 'react'
import { deleteProject, getFriendlyApiMessage, getProjects, updateProject } from '../api/api'

export default function ProjectLibrary({
  selectedProjectId,
  refreshKey,
  serviceAvailable = true,
  loadingProject = false,
  onOpenProject,
  onProjectUpdated,
  onProjectDeleted,
}) {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('')
  const [sourceType, setSourceType] = useState('')
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [nameDraft, setNameDraft] = useState('')
  const [savingId, setSavingId] = useState(null)

  useEffect(() => {
    let current = true
    setLoading(true)
    setError(null)
    const timer = window.setTimeout(async () => {
      try {
        const response = await getProjects({
          q: query.trim() || undefined,
          status: status || undefined,
          source_type: sourceType || undefined,
          limit: 500,
        })
        if (current) setProjects(response.data)
      } catch (err) {
        if (current) setError(getFriendlyApiMessage(err, 'loading saved projects'))
      } finally {
        if (current) setLoading(false)
      }
    }, query ? 220 : 0)

    return () => {
      current = false
      window.clearTimeout(timer)
    }
  }, [query, status, sourceType, refreshKey])

  const beginRename = (project) => {
    setEditingId(project.id)
    setNameDraft(project.name)
    setError(null)
  }

  const saveRename = async (event) => {
    event.preventDefault()
    if (!editingId || !nameDraft.trim()) return
    setSavingId(editingId)
    setError(null)
    try {
      const response = await updateProject(editingId, { name: nameDraft.trim() })
      setProjects((current) => current.map((project) => project.id === editingId ? response.data : project))
      onProjectUpdated?.(response.data)
      setEditingId(null)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'renaming this project'))
    } finally {
      setSavingId(null)
    }
  }

  const removeProject = async (project) => {
    if (!window.confirm(`Delete “${project.name}” and its saved artifacts and validation history? This cannot be undone.`)) return
    setSavingId(project.id)
    setError(null)
    try {
      await deleteProject(project.id)
      setProjects((current) => current.filter((item) => item.id !== project.id))
      if (selectedProjectId === project.id) onProjectDeleted?.(project.id)
    } catch (err) {
      setError(getFriendlyApiMessage(err, 'deleting this project'))
    } finally {
      setSavingId(null)
    }
  }

  return (
    <section id="projects" className="card project-library" aria-labelledby="project-library-title">
      <div className="project-library-heading">
        <div>
          <p className="aws-eyebrow">Saved work</p>
          <h2 id="project-library-title">Projects</h2>
          <p>Search, reopen, rename, or remove projects saved in MongoDB.</p>
        </div>
        <button type="button" className="aws-inline-button" onClick={() => window.location.hash = '#tier-1'}>
          Analyze a repository
        </button>
      </div>

      <div className="project-library-filters">
        <label className="project-search-label">
          <span className="sr-only">Search projects</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by project name or GitHub URL"
            aria-label="Search projects by name or GitHub URL"
          />
        </label>
        <label>
          <span className="sr-only">Filter by status</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)} aria-label="Filter projects by status">
            <option value="">All statuses</option>
            <option value="completed">Completed</option>
            <option value="analyzing">Analyzing</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
        </label>
        <label>
          <span className="sr-only">Filter by source</span>
          <select value={sourceType} onChange={(event) => setSourceType(event.target.value)} aria-label="Filter projects by source">
            <option value="">All sources</option>
            <option value="github_url">GitHub</option>
            <option value="zip_upload">ZIP upload</option>
          </select>
        </label>
      </div>

      {error && <div className="aws-notice" role="alert">{error}</div>}
      {loading ? (
        <p className="project-library-empty" role="status">Loading saved projects…</p>
      ) : projects.length === 0 ? (
        <div className="project-library-empty">
          {query || status || sourceType ? 'No projects match these filters.' : 'No saved projects yet. Analyze a GitHub repository or upload a ZIP to begin.'}
        </div>
      ) : (
        <div className="project-list" aria-live="polite">
          {projects.map((project) => (
            <article key={project.id} className={`project-list-row${selectedProjectId === project.id ? ' is-selected' : ''}`}>
              <div className="project-list-main">
                {editingId === project.id ? (
                  <form className="project-rename-form" onSubmit={saveRename}>
                    <label className="sr-only" htmlFor={`project-name-${project.id}`}>Project name</label>
                    <input
                      id={`project-name-${project.id}`}
                      value={nameDraft}
                      maxLength={120}
                      autoFocus
                      onChange={(event) => setNameDraft(event.target.value)}
                      required
                    />
                    <button type="submit" disabled={savingId === project.id || !nameDraft.trim()}>
                      {savingId === project.id ? 'Saving…' : 'Save'}
                    </button>
                    <button type="button" className="project-secondary-action" onClick={() => setEditingId(null)}>Cancel</button>
                  </form>
                ) : (
                  <>
                    <strong>{project.name}</strong>
                    <span>{project.source_type === 'github_url' ? 'GitHub repository' : 'ZIP upload'} · {project.status}</span>
                    {project.source_url && <code title={project.source_url}>{project.source_url}</code>}
                  </>
                )}
              </div>
              {editingId !== project.id && (
                <div className="project-list-actions">
                  <button type="button" onClick={() => onOpenProject(project.id)} disabled={!serviceAvailable || loadingProject || savingId === project.id || project.status === 'analyzing'}>
                    {selectedProjectId === project.id ? 'Opened' : 'Open'}
                  </button>
                  <button type="button" className="project-secondary-action" onClick={() => beginRename(project)} disabled={!serviceAvailable || loadingProject || savingId === project.id}>Rename</button>
                  <button type="button" className="project-delete-action" onClick={() => removeProject(project)} disabled={!serviceAvailable || loadingProject || savingId === project.id}>
                    {savingId === project.id ? 'Working…' : 'Delete'}
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      <p className="project-library-footnote">Showing the newest 500 matching projects.</p>
    </section>
  )
}
