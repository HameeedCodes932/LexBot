import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('lexbot_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('lexbot_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export async function loginUser(email, password) {
  const { data } = await api.post('/api/auth/login', { email, password })
  return data
}

export async function registerUser(username, email, password, firmName) {
  const { data } = await api.post('/api/auth/register', {
    username, email, password, firm_name: firmName,
  })
  return data
}

export async function getMe() {
  const { data } = await api.get('/api/auth/me')
  return data
}

// ── Profile ───────────────────────────────────────────────────────────────────
export async function updateProfile(data) {
  const res = await api.patch('/api/auth/me', data)
  return res.data
}

export async function uploadAvatar(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await api.post('/api/auth/avatar', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

// ── Chat ──────────────────────────────────────────────────────────────────────
export async function sendMessage(question, sessionId, provider = null, documentFilter = null) {
  const payload = { question, session_id: sessionId }
  if (provider) payload.provider = provider
  if (documentFilter && documentFilter.length > 0) payload.document_filter = documentFilter
  const { data } = await api.post('/api/chat', payload)
  return data
}

// ── Providers ─────────────────────────────────────────────────────────────────
export async function getProviders() {
  const { data } = await api.get('/api/providers')
  return data
}

// ── Documents ─────────────────────────────────────────────────────────────────
export async function uploadDocument(file, visibility = 'personal') {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/api/upload', form, { params: { visibility } })
  return data
}

export async function getDocuments(page = 1, pageSize = 20) {
  const { data } = await api.get('/api/documents', { params: { page, page_size: pageSize } })
  return data
}

export async function deleteDocument(documentId) {
  const { data } = await api.delete(`/api/documents/${documentId}`)
  return data
}

// ── Memory ────────────────────────────────────────────────────────────────────
export async function getMemory(sessionId) {
  const { data } = await api.get(`/api/memory/${sessionId}`)
  return data
}

export async function clearMemory(sessionId) {
  const { data } = await api.delete(`/api/memory/${sessionId}`)
  return data
}

// ── Clause Extraction ─────────────────────────────────────────────────────────
export async function extractClauses(documentName, clauseType) {
  const { data } = await api.post('/api/extract-clauses', {
    document_name: documentName, clause_type: clauseType,
  })
  return data
}

// ── Contract Comparison ───────────────────────────────────────────────────────
export async function compareClauses(documentOne, documentTwo, clauseType) {
  const { data } = await api.post('/api/compare-clauses', {
    document_one: documentOne, document_two: documentTwo, clause_type: clauseType,
  })
  return data
}

// ── Contract Summarization (Phase 4) ──────────────────────────────────────────
export async function summarizeDocument(documentName, summaryType = 'detailed') {
  const { data } = await api.post('/api/summarize', {
    document_name: documentName, summary_type: summaryType,
  })
  return data
}

// ── Obligation Tracker (Phase 4) ──────────────────────────────────────────────
export async function extractObligations(documentName) {
  const { data } = await api.post('/api/obligations/extract', {
    document_name: documentName,
  })
  return data
}

export async function getObligations(statusFilter = null, obligationType = null) {
  const params = {}
  if (statusFilter) params.status_filter = statusFilter
  if (obligationType) params.obligation_type = obligationType
  const { data } = await api.get('/api/obligations', { params })
  return data
}

export async function updateObligationStatus(obligationId, newStatus) {
  const { data } = await api.patch(`/api/obligations/${obligationId}/status`, {
    status: newStatus,
  })
  return data
}

export async function deleteObligation(obligationId) {
  const { data } = await api.delete(`/api/obligations/${obligationId}`)
  return data
}

// ── Template Matching (Phase 4) ───────────────────────────────────────────────
export async function getTemplates() {
  const { data } = await api.get('/api/templates')
  return data
}

export async function matchTemplate(documentName, templateId) {
  const { data } = await api.post('/api/templates/match', {
    document_name: documentName, template_id: templateId,
  })
  return data
}

// ── Table Extraction (Phase 4) ────────────────────────────────────────────────
export async function extractTables(documentName) {
  const { data } = await api.post('/api/extract-tables', {
    document_name: documentName,
  })
  return data
}

// ── Clause Library (Phase 4) ──────────────────────────────────────────────────
export async function saveClause(clauseType, content, title = '', sourceDocument = '', notes = '') {
  const { data } = await api.post('/api/clauses/save', {
    clause_type: clauseType, content, title, source_document: sourceDocument, notes,
  })
  return data
}

export async function getClauses(clauseType = null, benchmarksOnly = false) {
  const params = {}
  if (clauseType) params.clause_type = clauseType
  if (benchmarksOnly) params.benchmarks_only = true
  const { data } = await api.get('/api/clauses', { params })
  return data
}

export async function deleteClause(clauseId) {
  const { data } = await api.delete(`/api/clauses/${clauseId}`)
  return data
}

export async function toggleBenchmark(clauseId) {
  const { data } = await api.patch(`/api/clauses/${clauseId}/benchmark`)
  return data
}

// ── Admin ─────────────────────────────────────────────────────────────────────
export async function getAdminAnalytics() {
  const { data } = await api.get('/api/admin/analytics')
  return data
}

export async function getAdminUsers() {
  const { data } = await api.get('/api/admin/users')
  return data
}

export async function deactivateUser(userId) {
  const { data } = await api.patch(`/api/admin/users/${userId}/deactivate`)
  return data
}

// ── Multi-Tenancy & Enterprise (Phase 6) ──────────────────────────────────────
export async function createOrg(name) {
  const { data } = await api.post('/api/org', { name })
  return data
}

export async function getOrg() {
  const { data } = await api.get('/api/org')
  return data
}

export async function updateOrgSettings(settings) {
  const { data } = await api.patch('/api/org/settings', settings)
  return data
}

export async function inviteMember(email, role) {
  const { data } = await api.post('/api/org/invite', { email, role })
  return data
}

export async function getMembers() {
  const { data } = await api.get('/api/org/members')
  return data
}

export async function updateMemberRole(memberId, role) {
  const { data } = await api.patch(`/api/org/members/${memberId}/role`, { role })
  return data
}

export async function removeMember(memberId) {
  const { data } = await api.delete(`/api/org/members/${memberId}`)
  return data
}

export async function leaveOrg() {
  const { data } = await api.post('/api/org/leave')
  return data
}

export async function shareDocumentToOrg(documentId) {
  const { data } = await api.post(`/api/documents/${documentId}/share`)
  return data
}

export async function getOrgDocuments(page = 1, pageSize = 20) {
  const { data } = await api.get('/api/org/documents', { params: { page, page_size: pageSize } })
  return data
}

export async function getOrgAuditLogs(page = 1, pageSize = 20) {
  const { data } = await api.get('/api/org/audit-logs', { params: { page, page_size: pageSize } })
  return data
}

export async function configureSSO(provider, metadataUrl, entityId) {
  const { data } = await api.post('/api/org/sso/configure', { provider, metadata_url: metadataUrl, entity_id: entityId })
  return data
}

export async function createAPIKey(name, expiresInDays = null, scopes = null) {
  const payload = { name }
  if (expiresInDays) payload.expires_in_days = expiresInDays
  if (scopes) payload.scopes = scopes
  const { data } = await api.post('/api/org/api-keys', payload)
  return data
}

export async function getAPIKeys() {
  const { data } = await api.get('/api/org/api-keys')
  return data
}

export async function deleteAPIKey(keyId) {
  const { data } = await api.delete(`/api/org/api-keys/${keyId}`)
  return data
}

export async function createWebhook(url, events, secret = null) {
  const payload = { url, events }
  if (secret) payload.secret = secret
  const { data } = await api.post('/api/org/webhooks', payload)
  return data
}

export async function getWebhooks() {
  const { data } = await api.get('/api/org/webhooks')
  return data
}

export async function deleteWebhook(webhookId) {
  const { data } = await api.delete(`/api/org/webhooks/${webhookId}`)
  return data
}

export async function testWebhook(webhookId) {
  const { data } = await api.post(`/api/org/webhooks/${webhookId}/test`)
  return data
}

export async function runRetention() {
  const { data } = await api.post('/api/org/retention/run')
  return data
}

export async function getBranding(slug = null, domain = null) {
  const params = {}
  if (slug) params.slug = slug
  if (domain) params.domain = domain
  const { data } = await api.get('/api/org/branding', { params })
  return data
}

export async function uploadBrandingLogo(file) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await api.post('/api/org/branding/logo', form)
  return data
}

// ── Voice Transcription (Plan 2) ──────────────────────────────────────────────
export async function transcribeAudio(audioBlob) {
  const form = new FormData()
  form.append('file', audioBlob, 'recording.webm')
  const { data } = await api.post('/api/voice/transcribe', form)
  return data
}

// ── Annotations (Plan 2) ─────────────────────────────────────────────────────
export async function createAnnotation(documentId, annotationType, selectedText, comment, color = 'yellow') {
  const { data } = await api.post('/api/annotations', {
    document_id: documentId,
    annotation_type: annotationType,
    selected_text: selectedText,
    comment,
    color,
  })
  return data
}

export async function getAnnotations(documentId) {
  const { data } = await api.get('/api/annotations', { params: { document_id: documentId } })
  return data
}

export async function deleteAnnotation(annotationId) {
  const { data } = await api.delete(`/api/annotations/${annotationId}`)
  return data
}

export async function exportAnnotatedDocument(documentId) {
  const { data } = await api.get(`/api/export/document/${documentId}/annotated`, { responseType: 'blob' })
  return data
}

// ── Templates (Plan 2) ───────────────────────────────────────────────────────
export async function createTemplate(name, description, templateType, clauses) {
  const { data } = await api.post('/api/templates/create', { name, description, template_type: templateType, clauses })
  return data
}

export async function updateTemplate(templateId, updates) {
  const { data } = await api.put(`/api/templates/${templateId}`, updates)
  return data
}

export async function deleteTemplate(templateId) {
  const { data } = await api.delete(`/api/templates/${templateId}`)
  return data
}

// ── Language (Plan 2) ────────────────────────────────────────────────────────
export async function detectLanguage(text) {
  const { data } = await api.post('/api/language/detect', { text })
  return data
}

export async function getLanguages() {
  const { data } = await api.get('/api/languages')
  return data
}

// ── Clause Library share to firm (Plan 2) ────────────────────────────────────
export async function shareClauseToOrg(clauseId) {
  const { data } = await api.post(`/api/clauses/${clauseId}/share`)
  return data
}

// ── Agent ────────────────────────────────────────────────────────────────────
export async function runAgentCommand(command, context = '', sessionId = null) {
  const payload = { command, context }
  if (sessionId) payload.session_id = sessionId
  const { data } = await api.post('/api/agent', payload)
  return data
}

export async function getAgentTools() {
  const { data } = await api.get('/api/agent/tools')
  return data
}

export async function speakText(text) {
  const response = await api.post('/api/voice/speak', { text }, { responseType: 'blob' })
  return response.data
}

export default api
