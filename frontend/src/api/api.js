/**
 * api.js — Axios instance for communicating with the FastAPI backend.
 *
 * All requests automatically use the base URL from the VITE_API_BASE_URL
 * environment variable (falls back to localhost for local dev).
 */
import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ── Request interceptor: attach auth token when available ──────────────────
api.interceptors.request.use(
  (config) => {
    // Placeholder for future auth token injection
    return config
  },
  (error) => Promise.reject(error),
)

// ── Response interceptor: normalise errors ─────────────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ??
      error.message ??
      'Unknown error'
    console.error('[API Error]', message)
    return Promise.reject(error)
  },
)

// ── Health API ─────────────────────────────────────────────────────────────

/**
 * Fetch system health from GET /health.
 * @returns {Promise<HealthResponse>}
 */
export const fetchHealth = () => api.get('/health')

/**
 * Analyze a GitHub repository.
 * @param {string} url - The GitHub URL
 */
export const analyzeGithub = (url) => api.post('/repositories/analyze/github', { url }, { timeout: 180000 })

/**
 * Analyze a ZIP file upload.
 * @param {File} file - The ZIP file
 */
export const analyzeZip = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/repositories/analyze/zip', formData, {
    timeout: 180000,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * Get all analyzed projects.
 */
export const getProjects = (params = {}) => api.get('/projects', { params })

/**
 * Get a specific project by ID.
 * @param {string} id - The project UUID
 */
export const getProject = (id) => api.get(`/projects/${id}`)

/** Rename or delete a saved project and its persisted workflow history. */
export const updateProject = (id, updates) => api.patch(`/projects/${id}`, updates)
export const deleteProject = (id) => api.delete(`/projects/${id}`)

/**
 * Submit requirements to generate deployment artifacts.
 * @param {string} projectId 
 * @param {object} requirements 
 */
export const generateArtifacts = (projectId, requirements) => 
  api.post(`/projects/${projectId}/requirements`, requirements, { timeout: 120000 })

/**
 * Get generated artifacts for a project.
 * @param {string} projectId 
 */
export const getArtifacts = (projectId) => 
  api.get(`/projects/${projectId}/artifacts`)

export const downloadArtifactBundle = (projectId, generationId) =>
  api.get(`/projects/${projectId}/artifacts/${generationId}/download`, { responseType: 'blob' })

/**
 * Run validation on the latest artifacts.
 * @param {string} projectId 
 */
export const runValidation = (projectId) =>
  api.post(`/projects/${projectId}/validate`)

/**
 * Trigger AI repair.
 * @param {string} projectId 
 */
export const attemptRepair = (projectId) =>
  api.post(`/projects/${projectId}/repair`)

/**
 * Get unified generation and validation history.
 * @param {string} projectId 
 */
export const getProjectStatus = (projectId) =>
  api.get(`/projects/${projectId}/status`)

/**
 * Get deployment analysis (Security, Cost, Performance).
 * @param {string} projectId 
 */
export const getAnalysis = (projectId) =>
  api.get(`/projects/${projectId}/analysis`)

/**
 * Get deployment readiness score.
 * @param {string} projectId 
 */
export const getReadiness = (projectId) =>
  api.get(`/projects/${projectId}/readiness`)

/**
 * Trigger deployment to Kubernetes.
 * @param {string} projectId 
 */
export const triggerDeployment = (projectId, deploymentTarget) =>
  api.post(`/projects/${projectId}/deploy`, deploymentTarget)

/**
 * Get live deployment status from cluster.
 * @param {string} projectId 
 */
export const getDeployStatus = (projectId, namespace = 'default') =>
  api.get(`/projects/${projectId}/deploy/status`, { params: { namespace } })

/** Inspect the configured kubectl context without changing the cluster. */
export const getDeploymentTarget = () => api.get('/deployment-target')

/** Keep transport and server details out of the user-facing interface. */
export function getFriendlyApiMessage(error, action) {
  if (!error?.response) {
    if (error?.code === 'ECONNABORTED') {
      return `The request timed out while ${action}. Check the backend and try again.`
    }
    return `The local API could not be reached while ${action}. Check that the backend is running.`
  }

  if (error.response.status >= 500) {
    return 'The local service could not complete this action. Check its status and try again.'
  }

  const detail = error.response.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(' · ') || `Please review the submitted information and try ${action} again.`
  }
  return `Please review the submitted information and try ${action} again.`
}

export default api
