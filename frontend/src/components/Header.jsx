/** Top navigation styled after a cloud provider console. */
export default function Header({ version }) {
  return (
    <>
      <header className="aws-header">
        <div className="aws-header-main">
          <a className="aws-brand" href="#top" aria-label="AI DevOps Assistant home">
            <span className="aws-brand-mark">AD</span>
            <span className="aws-brand-title">AI DevOps Assistant</span>
          </a>

          <nav className="aws-nav" aria-label="Main navigation">
            <a href="#overview" className="active">Overview</a>
            <a href="#projects">Projects</a>
            <a href="#tier-1">Ingest</a>
            <a href="#tier-2">Generate</a>
            <a href="#tier-3">Validate</a>
            <a href="#tier-4">Governance</a>
            <a href="#services">Services</a>
          </nav>

          <div className="aws-header-meta">
            <span className="aws-environment">LOCAL DEVELOPMENT</span>
            <span className="aws-version">v{version ?? '—'}</span>
          </div>
        </div>
      </header>
      <div className="aws-subnav">
        <span>AI DevOps Assistant</span>
        <span className="aws-subnav-separator">›</span>
        <strong>Dashboard</strong>
        <span className="aws-subnav-spacer" />
        <span className="aws-region">Region: Local</span>
      </div>
    </>
  )
}
