import axios from 'axios'

const api = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Life Domains
export const getLifeDomains = (layer) => api.get('/api/life-domains' + (layer ? `?layer=${layer}` : ''))
export const createLifeDomain = (data) => api.post('/api/life-domains', data)
export const getLifeDomain = (id) => api.get(`/api/life-domains/${id}`)
export const updateLifeDomain = (id, data) => api.put(`/api/life-domains/${id}`, data)
export const deleteLifeDomain = (id) => api.delete(`/api/life-domains/${id}`)
export const createSubsection = (domainId, name, description) => {
  const formData = new FormData()
  formData.append('name', name)
  formData.append('description', description || '')
  return api.post(`/api/life-domains/${domainId}/subsections`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// Seed default domains
export const seedDomains = () => api.post('/api/seed')

// Thoughts
export const createThought = (data) => api.post('/api/thoughts', data)
export const getThoughts = (domainId) => api.get(`/api/life-domains/${domainId}/thoughts`)

// Documents
export const uploadDocument = (domainId, file) => {
  const formData = new FormData()
  if (domainId) {
    formData.append('life_domain_id', domainId)
  }
  formData.append('file', file)
  return api.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const getDocuments = (domainId) => api.get(`/api/life-domains/${domainId}/documents`)

// Research Notes
export const createResearchNote = (data) => api.post('/api/research/notes', data)
export const getResearchNotes = (domainId) => api.get('/api/research/notes', { params: { life_domain_id: domainId } })

// Deadlines
export const createDeadline = (data) => api.post('/api/deadlines', data)
export const getDeadlines = (domainId, status) => api.get('/api/deadlines', { params: { life_domain_id: domainId, status } })

// Daily Plans
export const createDailyPlan = (data) => api.post('/api/plans', data)
export const getDailyPlans = (domainId) => api.get('/api/plans', { params: { life_domain_id: domainId } })

// Chat
export const sendMessage = (data) => api.post('/api/chat', data)

// Layer-based Chat (new)
export const sendLayerMessage = (layer, message) => api.post('/api/chat/layer', { layer, message })
export const getLayerChatHistory = (layer) => api.get(`/api/chat/layer/${layer}`)

// Domain Documents (editable documents like Kaal Overview.md)
export const getDomainDocuments = (domainId) => api.get(`/api/life-domains/${domainId}/documents`)
export const createDomainDocument = (domainId, data) => api.post(`/api/life-domains/${domainId}/documents`, data)
export const updateDomainDocument = (domainId, docId, content) => api.put(`/api/life-domains/${domainId}/documents/${docId}`, { content })
