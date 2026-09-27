import axios from 'axios'

const API_BASE = 'http://localhost:8020'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Health
export const healthCheck = () => api.get('/api/health')

// Knowledge Operations
export const createKnowledgeObject = (data) => api.post('/api/knowledge/create', null, {
  params: data
})
export const getKnowledgeObject = (id) => api.get(`/api/knowledge/${id}`)
export const updateKnowledgeObject = (id, data) => api.patch(`/api/knowledge/${id}`, data)
export const archiveKnowledgeObject = (id) => api.post(`/api/knowledge/${id}/archive`)
export const restoreKnowledgeObject = (id) => api.post(`/api/knowledge/${id}/restore`)
export const getIdentityCard = (id) => api.get(`/api/knowledge/${id}/identity`)
export const searchKnowledge = (params) => api.get('/api/knowledge/', { params })
export const getNodeTypes = () => api.get('/api/knowledge/types/list')

// Graph Operations
export const createRelationship = (data) => api.post('/api/graph/relationship', data)
export const getNeighbors = (id) => api.get(`/api/graph/neighbors/${id}`)
export const getBacklinks = (id) => api.get(`/api/graph/backlinks/${id}`)
export const getForwardLinks = (id) => api.get(`/api/graph/forwardlinks/${id}`)
export const findPath = (sourceId, targetId) => api.get('/api/graph/path', {
  params: { source_id: sourceId, target_id: targetId }
})
export const queryGraph = (query) => api.post('/api/graph/query', { query })
export const getDegreeAnalysis = (id) => api.get(`/api/graph/degree/${id}`)
export const getSubgraph = (nodeIds, depth = 1) => api.get('/api/graph/subgraph', {
  params: { node_ids: Array.isArray(nodeIds) ? nodeIds.join(',') : nodeIds, depth }
})
export const getFullGraph = (maxNodes = 200) => api.get('/api/graph/full', {
  params: { max_nodes: maxNodes }
})

// Workspace Operations
export const getSidebar = () => api.get('/api/workspace/sidebar')
export const getDashboard = () => api.get('/api/workspace/dashboard')

// Asset Operations
export const uploadAsset = (file, autoExtract = true) => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('auto_extract', autoExtract)
  return api.post('/api/asset/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}
export const getAsset = (id) => api.get(`/api/asset/${id}`)
export const getAssetKnowledge = (id) => api.get(`/api/asset/${id}/knowledge`)
export const approveAssetKnowledge = (id, suggestionIndices = null) => 
  api.post(`/api/asset/${id}/approve`, null, { params: suggestionIndices || { approve_all: true } })

// Reasoning Operations
export const bringMeBack = (sinceDays = 7, format = 'json') => 
  api.post('/api/reasoning/bring-me-back', null, { params: { since_days: sinceDays, format } })
export const getProgress = (nodeId, sinceDays = 30) => 
  api.get('/api/reasoning/progress', { params: { node_id: nodeId, since_days: sinceDays } })
export const findGaps = (nodeId) => 
  api.get('/api/reasoning/gaps', { params: { node_id: nodeId } })
export const findContradictions = (nodeId) => 
  api.get('/api/reasoning/contradictions', { params: { node_id: nodeId } })
export const suggestNextSteps = (focusNodeId) => 
  api.post('/api/reasoning/suggest-next-steps', null, { params: { focus_node_id: focusNodeId } })
export const summarizeNode = (nodeId, maxLength = 500) => 
  api.post('/api/reasoning/summarize', null, { params: { node_id: nodeId, max_length: maxLength } })

// System Operations
export const getLLMStatus = () => api.get('/api/system/llm_status')
export const getDegradationFlags = () => api.get('/api/system/degradation_flags')

// ─── Phase 11-20: New Engine APIs ───

// Phase 11: Conversation Engine
export const getConversationStats = () => api.get('/api/v2/conversation/stats')

// Phase 12: Knowledge Pipeline
export const extractDocument = (content, formatHint = '', metadata = null) =>
  api.post('/api/v2/pipeline/extract', { content, format_hint: formatHint, metadata })

// Phase 13: Prediction Engine
export const getPredictions = () => api.get('/api/v2/predict/active')
export const submitPredictionFeedback = (predictionId, feedback, comment = '') =>
  api.post('/api/v2/predict/feedback', { prediction_id: predictionId, feedback, comment })

// Phase 14: Personal Model
export const getPersonalModel = () => api.get('/api/v2/personal-model')
export const updatePersonalAttribute = (path, value, confidence = 0.5) =>
  api.post('/api/v2/personal-model/update', { path, value, confidence })
export const getAttributeHistory = (path) => api.get(`/api/v2/personal-model/history/${path}`)

// Phase 15: World Model
export const getWorldObservations = (days = 7) => api.get('/api/v2/world/observations', { params: { days } })
export const getOpportunities = (minConfidence = 0.5) => api.get('/api/v2/world/opportunities', { params: { min_confidence: minConfidence } })

// Phase 16: Dashboard
export const getDashboardPanels = () => api.get('/api/v2/dashboard/panels')
export const getPanelData = (panelId, refresh = false) => api.get(`/api/v2/dashboard/panel/${panelId}`, { params: { refresh } })

// Phase 17: Security
export const getSecurityAuditLog = (limit = 100) => api.get('/api/v2/security/audit-log', { params: { limit } })
export const getSecurityStats = () => api.get('/api/v2/security/stats')

// Phase 18: Infrastructure
export const getInfrastructureStatus = () => api.get('/api/v2/infrastructure/status')

// Phase 19: Technology Decisions
export const getTechDecisions = (phase = null) => api.get('/api/v2/tech-decisions', { params: phase ? { phase } : {} })

// Phase 20: Implementation Roadmap
export const getRoadmap = () => api.get('/api/v2/roadmap')
export const getRoadmapProgress = () => api.get('/api/v2/roadmap/progress')

// Phase 09: Learning Engine
export const ingestLearningSignal = (payload) => api.post('/api/v2/learning/signal', payload)
export const getLearningStats = () => api.get('/api/v2/learning/stats')
export const getLearningSignals = () => api.get('/api/v2/learning/signals')

// Phase 10: Execution Engine
export const proposeTask = (payload) => api.post('/api/v2/execute/propose_task', payload)
export const getPendingTasks = () => api.get('/api/v2/execute/tasks/pending')
export const approveTask = (taskId, payload) => api.post(`/api/v2/execute/tasks/${taskId}/approve`, payload)
export const getAuditLog = () => api.get('/api/v2/execute/audit-log')

// Phase 11: Conversation Engine
export const processChatTurn = (payload) => api.post('/api/v2/chat/turn', payload)
export const getConversationSessions = () => api.get('/api/v2/conversation/sessions')
export const getSessionTurns = (sessionId) => api.get(`/api/v2/conversation/sessions/${sessionId}/turns`)

// Phase 12: Knowledge Pipeline
export const runPipelineExtract = (payload) => api.post('/api/v2/pipeline/extract', payload)
export const connectSyncSource = (payload) => api.post('/api/v2/pipeline/connect_source', payload)
export const getConnectedSources = () => api.get('/api/v2/pipeline/sources')
export const getPipelineRuns = () => api.get('/api/v2/pipeline/runs')

// Chat Operations
export const sendChatMessage = (layer, message) => 
  api.post('/api/chat/message', null, { params: { layer, message } })
export const getChatHistory = (layer, limit = 50) => 
  api.get(`/api/chat/history/${layer}`, { params: { limit } })
export const clearChatHistory = (layer) => 
  api.delete(`/api/chat/history/${layer}`)
