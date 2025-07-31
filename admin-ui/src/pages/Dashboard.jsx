import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material'
import {
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Storage,
  Speed,
  Search,
  Memory,
} from '@mui/icons-material'
import { healthAPI, vectorAPI } from '../services/api'

function Dashboard() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [health, setHealth] = useState(null)
  const [stats, setStats] = useState(null)
  const [metrics, setMetrics] = useState(null)

  useEffect(() => {
    fetchDashboardData()
    const interval = setInterval(fetchDashboardData, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const fetchDashboardData = async () => {
    try {
      setLoading(true)
      const [healthRes, statsRes, metricsRes] = await Promise.all([
        healthAPI.getHealth(),
        vectorAPI.getStats(),
        healthAPI.getMetricsSummary(),
      ])
      
      setHealth(healthRes.data)
      setStats(statsRes.data)
      setMetrics(metricsRes.data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle color="success" />
      case 'warning':
        return <Warning color="warning" />
      default:
        return <ErrorIcon color="error" />
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'success'
      case 'warning':
        return 'warning'
      default:
        return 'error'
    }
  }

  if (loading && !health) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error loading dashboard: {error}
      </Alert>
    )
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        System Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {/* System Status Card */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                {getStatusIcon(health?.status || metrics?.status)}
                <Typography variant="h6" ml={1}>
                  System Status
                </Typography>
              </Box>
              <Chip
                label={health?.status || metrics?.status || 'Unknown'}
                color={getStatusColor(health?.status || metrics?.status)}
                sx={{ mb: 1 }}
              />
              <Typography variant="body2" color="text.secondary">
                Uptime: {metrics?.uptime_hours?.toFixed(1) || 0} hours
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Requests: {metrics?.total_requests || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Vector Database Card */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Storage color="primary" />
                <Typography variant="h6" ml={1}>
                  Vector Database
                </Typography>
              </Box>
              <Typography variant="h4">
                {stats?.total_vectors?.toLocaleString() || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Vectors
              </Typography>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Model: {stats?.model_name || 'Not loaded'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Card */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Speed color="primary" />
                <Typography variant="h6" ml={1}>
                  Performance
                </Typography>
              </Box>
              <Typography variant="h4">
                {metrics?.error_rate?.toFixed(1) || 0}%
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Error Rate
              </Typography>
              <Typography variant="body2" color="text.secondary" mt={1}>
                Alerts: {metrics?.alerts || 0}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Index Status Card */}
        <Grid item xs={12} md={6} lg={3}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" mb={2}>
                <Memory color="primary" />
                <Typography variant="h6" ml={1}>
                  Index Status
                </Typography>
              </Box>
              <Chip
                label={health?.vector_db_ready ? 'Ready' : 'Not Ready'}
                color={health?.vector_db_ready ? 'success' : 'warning'}
                size="small"
                sx={{ mb: 1 }}
              />
              <Typography variant="body2" color="text.secondary">
                Dimension: {stats?.dimension || 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Index Type: {stats?.index_type || 'N/A'}
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Quick Stats */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quick Statistics
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center" p={2}>
                    <Search fontSize="large" color="primary" />
                    <Typography variant="h6">
                      {stats?.metadata_count?.toLocaleString() || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Searchable Cases
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center" p={2}>
                    <Storage fontSize="large" color="primary" />
                    <Typography variant="h6">
                      {((stats?.total_vectors || 0) * 384 * 4 / 1024 / 1024).toFixed(1)} MB
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Estimated Index Size
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center" p={2}>
                    <Speed fontSize="large" color="primary" />
                    <Typography variant="h6">
                      {stats?.is_trained ? 'Trained' : 'Not Trained'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Training Status
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center" p={2}>
                    <Memory fontSize="large" color="primary" />
                    <Typography variant="h6">
                      384
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Embedding Dimension
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default Dashboard