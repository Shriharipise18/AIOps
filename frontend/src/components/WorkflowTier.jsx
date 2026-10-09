export default function WorkflowTier({ number, id, title, description, status, children }) {
  return (
    <section id={id} className="workflow-tier">
      <header className="workflow-tier-heading">
        <span className="workflow-tier-number" aria-hidden="true">{number}</span>
        <div className="workflow-tier-copy">
          <p className="aws-eyebrow">Tier {number}</p>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
        <span className="workflow-tier-status">{status}</span>
      </header>
      <div className="workflow-tier-content">{children}</div>
    </section>
  )
}
