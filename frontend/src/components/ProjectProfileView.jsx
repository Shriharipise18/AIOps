export default function ProjectProfileView({ project }) {
  if (!project) return null

  const profile = project.profile
  if (!profile) return (
    <div className="card" style={{ padding: '2rem', textAlign: 'center', color: 'var(--aws-muted)' }}>
      This repository did not produce an analysis profile. Check that its source files include a supported project manifest, then try again.
    </div>
  )

  const Item = ({ label, value }) => (
    <div style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--aws-border)' }}>
      <span style={{ display: 'inline-block', width: '140px', fontSize: '0.75rem', color: 'var(--aws-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </span>
      <span style={{ fontSize: '0.9rem', color: 'var(--aws-text)', fontWeight: 500 }}>
        {value || <span style={{ color: 'var(--aws-muted)' }}>None</span>}
      </span>
    </div>
  )

  return (
    <div className="card animate-slide-up">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--aws-text)', margin: 0 }}>
          Project Profile
        </h2>
        <span className="workflow-project-name">{project.name}</span>
      </div>

      <div className="workflow-profile-grid">
        {/* Core Stack */}
        <div>
          <h3>Core stack</h3>
          <Item label="Language" value={profile.language} />
          <Item label="Framework" value={profile.framework} />
          <Item label="Package Manager" value={profile.package_manager} />
          <Item label="Entrypoint" value={profile.entrypoint} />
        </div>

        {/* Configuration */}
        <div>
          <h3>Runtime configuration</h3>
          <Item label="Port" value={profile.port} />
          <Item label="Build Command" value={profile.build_command} />
          <Item label="Start Command" value={profile.start_command} />
        </div>

        {/* Infrastructure */}
        <div>
          <h3>External services</h3>
          <Item label="Database" value={profile.database} />
          <Item label="Redis" value={profile.redis ? 'Yes' : 'No'} />
          <Item label="Queue" value={profile.queue} />
        </div>

        <div>
          <h3>Dependencies</h3>
          {Object.keys(profile.dependencies || {}).length ? (
            <ul className="workflow-profile-list">
              {Object.entries(profile.dependencies).slice(0, 12).map(([name, version]) => (
                <li key={name}><span>{name}</span><code>{version}</code></li>
              ))}
            </ul>
          ) : <p className="workflow-profile-empty">No dependency manifest detected.</p>}
        </div>
      </div>

      <div className="workflow-profile-extras">
        <div>
          <h3>Environment variable names</h3>
          <div className="workflow-profile-chips">
            {(profile.env_vars || []).length
              ? profile.env_vars.slice(0, 18).map((name) => <code key={name}>{name}</code>)
              : <span className="workflow-profile-empty">None detected</span>}
          </div>
          <p className="workflow-footnote">Only variable names are shown; values are not read into the profile.</p>
        </div>
        <details className="workflow-file-inventory">
          <summary>Source inventory <span>{profile.raw_files?.length || 0} files</span></summary>
          <ul>
            {(profile.raw_files || []).slice(0, 100).map((file) => <li key={file}><code>{file}</code></li>)}
          </ul>
          {(profile.raw_files || []).length > 100 && <small>Showing the first 100 files of a bounded inventory.</small>}
        </details>
      </div>
    </div>
  )
}
