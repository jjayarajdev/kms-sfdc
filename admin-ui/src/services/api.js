import axios from 'axios'

const API_BASE_URL = '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
})

// Health & Monitoring APIs
export const healthAPI = {
  getHealth: () => api.get('/health'),
  getDetailedHealth: () => api.get('/health/detailed'),
  getHealthReport: (hours = 24) => api.get(`/health/report?hours=${hours}`),
  getMetricsSummary: () => api.get('/health/metrics'),
}

// Performance APIs
export const performanceAPI = {
  getReport: () => api.get('/performance/report'),
  getOperationStats: (operation) => 
    api.get('/performance/operations', { params: { operation } }),
  getBatchPerformance: () => api.get('/performance/batch'),
  getRecommendations: () => api.get('/performance/recommendations'),
  saveMetrics: () => api.post('/performance/save'),
}

// Vector Database APIs
export const vectorAPI = {
  getStats: () => api.get('/stats'),
  search: (query, topK = 10, threshold = 0.4) => 
    api.post('/search', { query, top_k: topK, similarity_threshold: threshold }),
  rebuildIndex: () => api.post('/rebuild-index'),
}

// Mock APIs for features not yet implemented in backend
export const backupAPI = {
  listBackups: async () => {
    // Mock data until backend endpoint is ready
    return {
      data: [
        {
          id: '20240129_120000',
          timestamp: '2024-01-29T12:00:00',
          description: 'Automatic daily backup',
          index_size_mb: 45.2,
          metadata_size_mb: 12.3,
        },
        {
          id: '20240128_120000',
          timestamp: '2024-01-28T12:00:00',
          description: 'Pre-update backup',
          index_size_mb: 44.8,
          metadata_size_mb: 12.1,
        },
      ]
    }
  },
  createBackup: (description) => 
    api.post('/backup/create', { description }),
  restoreBackup: (backupId) => 
    api.post(`/backup/restore/${backupId}`),
  deleteBackup: (backupId) => 
    api.delete(`/backup/${backupId}`),
}

export default api