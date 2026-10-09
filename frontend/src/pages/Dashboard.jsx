/** Main four-tier workflow for the AI-Powered DevOps Assistant. */
import { useEffect, useState } from 'react'
import { useHealth } from '../hooks/useHealth'
import Header from '../components/Header'
import RepoAnalyzer from '../components/RepoAnalyzer'
import ProjectProfileView from '../components/ProjectProfileView'
import DeploymentPlanner from '../components/DeploymentPlanner'
import ArtifactViewer from '../components/ArtifactViewer'
import ValidationLoop from '../components/ValidationLoop'
import DeploymentAnalysis from '../components/DeploymentAnalysis'
import DeploymentEngine from '../components/DeploymentEngine'
import PipelineVisualizer from '../components/PipelineVisualizer'
import WorkflowTier from '../components/WorkflowTier'
import RuntimeServices from '../components/RuntimeServices'
import ProjectLibrary from '../components/ProjectLibrary'
import { API_BASE_URL } from '../api/api'
import { getArtifacts, getFriendlyApiMessage, getProject } from '../api/api'

function getBackendStatus(data, error, loading) {
  if (loading) return 'loading'
  if (data) return 'ok'
  return error ? 'disconnected' : 'loading'
}

function StagePlaceholder({ title, children }) {
  return (
    <div className="workflow-placeholder">
      <strong>{title}</strong>
      <p>{children}</p>
    </div>
  )
}

export default function Dashboard() {
  const { data, loading, error, refetch } = useHealth()
  const [analyzedProject, setAnalyzedProject] = useState(null)
  const [generatedArtifacts, setGeneratedArtifacts] = useState(null)
  const [validationStatus, setValidationStatus] = useState(null)
  const [readiness, setReadiness] = useState(null)
  const [deployment, setDeployment] = useState(null)
  const [deploymentTarget, setDeploymentTarget] = useState(null)
  const [projectRefreshKey, setProjectRefreshKey] = useState(0)
  const [workspaceLoading, setWorkspaceLoading] = useState(false)
  const [workspaceError, setWorkspaceError] = useState(null)

  async function openProject(projectId) {
    setWorkspaceLoading(true)
    setWorkspaceError(null)
    try {
      const [projectResponse, artifactsResponse] = await Promise.all([
        getProject(projectId),
        getArtifacts(projectId),
      ])
      const project = projectResponse.data
      setAnalyzedProject(project)
      setGeneratedArtifacts(artifactsResponse.data[0] || null)
      setValidationStatus(null)
      setReadiness(null)
      setDeployment(null)
      setDeploymentTarget(null)
      try { window.localStorage.setItem('devops-assistant:selected-project', project.id) } catch { /* storage is optional */ }
      window.location.hash = '#overview'
    } catch (err) {
      setWorkspaceError(getFriendlyApiMessage(err, 'opening this project'))
    } finally {
      setWorkspaceLoading(false)
    }
  }

  function handleProjectCreated(project) {
    setAnalyzedProject(project)
    setGeneratedArtifacts(null)
    setValidationStatus(null)
    setReadiness(null)
    setDeployment(null)
    setDeploymentTarget(null)
    setWorkspaceError(null)
    try { window.localStorage.setItem('devops-assistant:selected-project', project.id) } catch { /* storage is optional */ }
  }

  function clearActiveProject() {
    setAnalyzedProject(null)
    setGeneratedArtifacts(null)
    setValidationStatus(null)
    setReadiness(null)
    setDeployment(null)
    setDeploymentTarget(null)
    try { window.localStorage.removeItem('devops-assistant:selected-project') } catch { /* storage is optional */ }
  }

  useEffect(() => {
    let active = true
    let savedProjectId = null
    try { savedProjectId = window.localStorage.getItem('devops-assistant:selected-project') } catch { /* storage is optional */ }
    if (savedProjectId) {
      setWorkspaceLoading(true)
      Promise.all([getProject(savedProjectId), getArtifacts(savedProjectId)])
        .then(([projectResponse, artifactsResponse]) => {
          if (!active) return
          setAnalyzedProject(projectResponse.data)
          setGeneratedArtifacts(artifactsResponse.data[0] || null)
        })
        .catch((err) => {
          if (!active) return
          if (err?.response?.status === 404) {
            try { window.localStorage.removeItem('devops-assistant:selected-project') } catch { /* storage is optional */ }
          } else {
            setWorkspaceError(getFriendlyApiMessage(err, 'restoring the last project'))
          }
        })
        .finally(() => {
          if (active) setWorkspaceLoading(false)
        })
    }
    return () => { active = false }
  }, [])

  const backendStatus = getBackendStatus(data, error, loading)
  const databaseStatus = loading ? 'loading' : (data?.services?.database?.status ?? 'disconnected')
  const redisStatus = loading ? 'loading' : (data?.services?.redis?.status ?? 'disconnected')
  const aiStatus = loading ? 'loading' : (data?.services?.ai?.status ?? 'not_configured')
  const aiProvider = data?.services?.ai?.provider || 'Groq'
  const aiKeyName = aiProvider === 'OpenAI' ? 'OPENAI_API_KEY' : 'GROQ_API_KEY'
  const overallStatus = !data ? (error ? 'disconnected' : 'loading') : (data.status === 'error' ? 'attention' : data.status)
  const overallColor = overallStatus === 'ok' ? 'var(--aws-success)' : overallStatus === 'degraded' || overallStatus === 'attention' ? 'var(--aws-warning)' : 'var(--aws-muted)'
  const overallLabel = overallStatus === 'ok' && redisStatus === 'disabled'
    ? 'Core services operational'
    : overallStatus === 'ok'
      ? 'All systems operational'
      : overallStatus === 'disconnected'
        ? 'Local API is not connected'
        : overallStatus === 'degraded' || overallStatus === 'attention'
          ? 'Some services need attention'
          : 'Checking service status…'
  const serviceAvailable = data?.services?.database?.status === 'ok' && !error

  const pipelineStatuses = {
    source: analyzedProject ? 'passed' : 'running',
    analysis: analyzedProject?.profile ? 'passed' : 'pending',
    generation: generatedArtifacts ? 'passed' : analyzedProject ? 'running' : 'pending',
    validation: validationStatus === 'passed' ? 'passed' : validationStatus === 'failed' ? 'failed' : generatedArtifacts ? 'needs-review' : 'pending',
    readiness: readiness ? (readiness.is_ready ? 'passed' : 'needs-review') : generatedArtifacts ? 'running' : 'pending',
    deployment: deployment?.status === 'success' ? 'passed' : deploymentTarget?.available && readiness?.is_ready ? 'needs-review' : 'pending',
  }

  const validationLabel = validationStatus === 'passed'
    ? 'Validation passed'
    : validationStatus === 'failed'
      ? 'Review findings'
      : generatedArtifacts ? 'Ready to validate' : 'Waiting for artifacts'

  const governanceLabel = deployment?.status === 'success'
    ? 'Deployment complete'
    : readiness ? (readiness.is_ready ? (deploymentTarget?.available ? 'Ready to deploy' : 'Configure cluster target') : 'Review score')
      : generatedArtifacts ? 'Analysis in progress' : 'Waiting for artifacts'

  return (
    <div id="top" className="aws-app">
      <Header version={data?.version} />

      <main id="overview" className="aws-main">
        <section className="animate-fade-in aws-hero">
          <div className="workflow-hero-copy">
            <p className="aws-eyebrow">FROM CODE TO PRODUCTION</p>
            <h1 className="aws-title">AI-Powered DevOps Assistant</h1>
            <p className="aws-description">Analyze repository code, generate deployment infrastructure, validate it, and review readiness before deployment.</p>
            <div className="workflow-hero-sequence" aria-label="Analyze, generate, validate, deploy, optimize">
              <span>Analyze</span><i>·</i><span>Generate</span><i>·</i><span>Validate</span><i>·</i><span>Deploy</span><i>·</i><span>Optimize</span>
            </div>
          </div>

          <div className="card aws-status-card" style={{ borderTopColor: overallColor }}>
            <p className="aws-status-label">System status</p>
            <p className="aws-status-value" style={{ color: overallColor }}>
              {overallStatus === 'loading' ? '…' : overallStatus === 'disconnected' ? 'WAITING' : overallStatus.toUpperCase()}
            </p>
            <p className="aws-status-caption">{overallLabel}</p>
            {overallStatus !== 'ok' && (
              <button className="aws-retry-button" type="button" onClick={refetch} disabled={loading}>
                {loading ? 'Checking…' : 'Retry connection'}
              </button>
            )}
          </div>
        </section>

        <PipelineVisualizer statuses={pipelineStatuses} />

        <ProjectLibrary
          selectedProjectId={analyzedProject?.id}
          refreshKey={projectRefreshKey}
          serviceAvailable={serviceAvailable}
          loadingProject={workspaceLoading}
          onOpenProject={openProject}
          onProjectUpdated={(updated) => setAnalyzedProject((current) => current?.id === updated.id ? updated : current)}
          onProjectDeleted={(deletedId) => {
            if (analyzedProject?.id === deletedId) clearActiveProject()
          }}
        />
        {workspaceLoading && <div className="aws-notice" role="status">Loading the saved project and latest artifact revision…</div>}
        {workspaceError && <div className="aws-notice" role="alert">{workspaceError}</div>}

        <div className="workflow-tier-list">
          <WorkflowTier
            number="1"
            id="tier-1"
            title="Ingestion & Heuristic Analysis"
            description="Bring in a GitHub repository or ZIP and build a deterministic profile of its runtime and dependencies."
            status={analyzedProject ? 'Analysis ready' : 'Start with a repository'}
          >
            <div className="workflow-tier-grid">
              <div>
                <div className="workflow-stage-heading"><span>01</span><div><strong>Input source</strong><small>GitHub repository or ZIP archive</small></div></div>
                <RepoAnalyzer
                  serviceAvailable={serviceAvailable}
                  onAnalyzed={handleProjectCreated}
                  onAttemptCompleted={() => setProjectRefreshKey((key) => key + 1)}
                />
              </div>
              <aside className="workflow-tier-aside">
                <div className="workflow-stage-heading"><span>02</span><div><strong>Repository analyzer</strong><small>Static inspection only</small></div></div>
                <ul className="workflow-feature-list">
                  <li>Language, framework and package manager</li>
                  <li>Entrypoint, start command and listening port</li>
                  <li>Dependencies and environment variable names</li>
                  <li>Database, cache and queue indicators</li>
                  <li>Source file inventory and deployment profile</li>
                </ul>
                <p className="workflow-footnote">Repository code is inspected as text and is not executed during analysis.</p>
              </aside>
            </div>
            {analyzedProject && <ProjectProfileView project={analyzedProject} />}
          </WorkflowTier>

          <WorkflowTier
            number="2"
            id="tier-2"
            title="Intelligent Synthesis & Generation"
            description="Turn the repository profile and deployment requirements into a deterministic deployment specification and artifact bundle."
            status={generatedArtifacts ? 'Artifacts generated' : analyzedProject ? 'Ready to configure' : 'Waiting for analysis'}
          >
            {analyzedProject?.profile ? (
              <>
                <div className="workflow-stage-heading"><span>03</span><div><strong>Infrastructure generator</strong><small>Configure target and resource requirements</small></div></div>
                <DeploymentPlanner project={analyzedProject} serviceAvailable={serviceAvailable} onGenerated={(artifacts) => {
                  setGeneratedArtifacts(artifacts)
                  setValidationStatus(null)
                  setReadiness(null)
                  setDeployment(null)
                }} />
                <p className="workflow-generator-note">{aiStatus === 'configured' ? `${aiProvider} is configured (${data?.services?.ai?.model || 'selected model'}) for generation and repair. Local templates remain available if the API request fails.` : `${aiProvider} is not configured yet. Add ${aiKeyName} to backend/.env and restart the backend to enable AI generation and repair. Local templates work without the key.`}</p>
                {generatedArtifacts && <ArtifactViewer generation={generatedArtifacts} projectId={analyzedProject.id} />}
              </>
            ) : (
              <StagePlaceholder title="Generated output follows repository analysis">
                {analyzedProject ? 'This saved project has no completed repository profile. Re-analyze its source to create one.' : 'The generator can produce a Dockerfile, Kubernetes manifests and Helm chart, or a Docker Compose bundle, plus a GitHub Actions quality workflow.'}
              </StagePlaceholder>
            )}
          </WorkflowTier>

          <WorkflowTier
            number="3"
            id="tier-3"
            title="Closed-Loop Validation & Self-Healing"
            description="Run deterministic checks against generated files, inspect findings, and create a corrected artifact revision."
            status={validationLabel}
          >
            {generatedArtifacts ? (
              <div className="workflow-tier-grid">
                <div>
                  <div className="workflow-stage-heading"><span>04</span><div><strong>Validation pipeline</strong><small>Validate, review, and repair</small></div></div>
                  <ValidationLoop
                    projectId={analyzedProject.id}
                    serviceAvailable={serviceAvailable}
                    onUpdateArtifacts={(artifacts) => {
                      setGeneratedArtifacts(artifacts)
                      setValidationStatus(null)
                      setReadiness(null)
                      setDeployment(null)
                    }}
                    onStatusChange={setValidationStatus}
                  />
                </div>
                <aside className="workflow-tier-aside">
                  <ul className="workflow-check-list">
                    <li>YAML structure and required Kubernetes resources</li>
                    <li>Port, replica and Dockerfile consistency</li>
                    <li>Basic container and manifest security rules</li>
                    <li>Validation history and repair revisions</li>
                  </ul>
                  <p className="workflow-footnote">These are built-in deterministic checks. External scanners such as Trivy or Hadolint are not configured in this workspace.</p>
                </aside>
              </div>
            ) : (
              <StagePlaceholder title="Validation starts after generation">
                The quality gate checks generated artifacts before governance and deployment review.
              </StagePlaceholder>
            )}
          </WorkflowTier>

          <WorkflowTier
            number="4"
            id="tier-4"
            title="Governance & Orchestration"
            description="Review security heuristics, cost estimates and performance readiness, then inspect the Kubernetes deployment target."
            status={governanceLabel}
          >
            {generatedArtifacts ? (
              <>
                <div className="workflow-stage-heading"><span>05</span><div><strong>Readiness & scoring</strong><small>Security · Cost · Performance</small></div></div>
                <DeploymentAnalysis projectId={analyzedProject.id} />
                <div className="workflow-stage-heading workflow-stage-heading-spaced"><span>06</span><div><strong>Kubernetes deployment target</strong><small>Cluster readiness and deployment orchestration</small></div></div>
                <DeploymentEngine
                  projectId={analyzedProject.id}
                  serviceAvailable={serviceAvailable}
                  lastDeployment={analyzedProject.last_deployment}
                  supportsKubernetes={!generatedArtifacts['docker-compose.yml']}
                  onReadinessChange={setReadiness}
                  onDeploymentChange={setDeployment}
                  onTargetChange={setDeploymentTarget}
                />
                <div className="workflow-observability-note">
                  <strong>Runtime visibility</strong>
                  <span>Cluster pod and service status is read after deployment. Prometheus, Grafana, logs, and alerting need separate cluster integrations.</span>
                </div>
              </>
            ) : (
              <StagePlaceholder title="Governance follows validation">
                Readiness scoring, AWS cost estimation and deployment orchestration appear here once infrastructure artifacts are generated.
              </StagePlaceholder>
            )}
          </WorkflowTier>
        </div>

        <RuntimeServices
          backendStatus={backendStatus}
          mongoStatus={databaseStatus}
          mongoLatency={data?.services?.database?.latency_ms}
          redisStatus={redisStatus}
          redisLatency={data?.services?.redis?.latency_ms}
          aiStatus={aiStatus}
          aiProvider={aiProvider}
          aiKeyName={aiKeyName}
          aiModel={data?.services?.ai?.model}
          version={data?.version}
          environment={data?.environment}
          apiBaseUrl={API_BASE_URL}
        />
      </main>

      <footer className="aws-footer">AI-Powered DevOps Assistant <span>·</span> {new Date().getFullYear()}</footer>
    </div>
  )
}
