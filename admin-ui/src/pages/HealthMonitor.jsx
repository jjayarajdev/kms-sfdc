import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  LinearProgress,
  Chip,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material'
import {
  CheckCircle,
  Warning,
  Error as ErrorIcon,
  Memory,
  Storage,
  Speed,
  DataUsage,
} from '@mui/icons-material'
import { healthAPI } from '../services/api'

function HealthMonitor() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [healthData, setHealthData] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    fetchHealthData()
    const interval = setInterval(() => {
      setRefreshing(true)
      fetchHealthData()
    }, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  const fetchHealthData = async () => {
    try {
      const response = await healthAPI.getDetailedHealth()
      setHealthData(response.data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const getAlertIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return <ErrorIcon color="error" />
      case 'warning':
        return <Warning color="warning" />
      default:
        return <CheckCircle color="success" />
    }
  }

  const formatBytes = (bytes) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    if (bytes < 1024 * 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB'
    return (bytes / 1024 / 1024 / 1024).toFixed(1) + ' GB'
  }

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    )
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Error loading health data: {error}
      </Alert>
    )
  }

  const systemCheck = healthData?.checks?.system || {}
  const indexCheck = healthData?.checks?.index || {}
  const performanceCheck = healthData?.checks?.performance || {}
  const dataCheck = healthData?.checks?.data || {}
  const alerts = healthData?.alerts || []

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Health Monitor</Typography>
        {refreshing && <CircularProgress size={24} />}
      </Box>

      {/* Overall Status */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={2}>
            {getAlertIcon(healthData?.status === 'healthy' ? 'success' : healthData?.status)}
            <Typography variant="h6">
              System Health: {healthData?.status?.toUpperCase()}
            </Typography>
            <Typography variant="body2" color="text.secondary" ml="auto">
              Last checked: {new Date(healthData?.timestamp).toLocaleString()}
            </Typography>
          </Box>
        </CardContent>
      </Card>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Active Alerts ({alerts.length})
            </Typography>
            <List>
              {alerts.map((alert, index) => (
                <ListItem key={index}>
                  <ListItemIcon>
                    {getAlertIcon(alert.severity)}
                  </ListItemIcon>
                  <ListItemText
                    primary={alert.message}
                    secondary={`Type: ${alert.type} | Value: ${alert.value || 'N/A'}`}
                  />
                  <Chip
                    label={alert.severity}
                    color={alert.severity === 'critical' ? 'error' : 'warning'}
                    size="small"
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      )}

      <Grid container spacing={3}>
        {/* System Resources */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Memory sx={{ mr: 1, verticalAlign: 'middle' }} />
                System Resources
              </Typography>
              
              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">CPU Usage</Typography>
                  <Typography variant="body2">
                    {systemCheck.cpu_usage_percent?.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={systemCheck.cpu_usage_percent || 0}
                  color={systemCheck.cpu_usage_percent > 80 ? 'error' : 'primary'}
                />
              </Box>

              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Memory Usage</Typography>
                  <Typography variant="body2">
                    {systemCheck.memory_usage_percent?.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={systemCheck.memory_usage_percent || 0}
                  color={systemCheck.memory_usage_percent > 80 ? 'error' : 'primary'}
                />
              </Box>

              <Box mb={2}>
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Typography variant="body2">Disk Usage</Typography>
                  <Typography variant="body2">
                    {systemCheck.disk_usage_percent?.toFixed(1)}%
                  </Typography>
                </Box>
                <LinearProgress
                  variant="determinate"
                  value={systemCheck.disk_usage_percent || 0}
                  color={systemCheck.disk_usage_percent > 90 ? 'error' : 'primary'}
                />
              </Box>

              <Typography variant="body2" color="text.secondary">
                Available Memory: {systemCheck.memory_available_gb?.toFixed(2)} GB
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Free Disk Space: {systemCheck.disk_free_gb?.toFixed(2)} GB
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Process Memory: {systemCheck.process_memory_mb?.toFixed(0)} MB
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        {/* Index Health */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Storage sx={{ mr: 1, verticalAlign: 'middle' }} />
                Index Health
              </Typography>
              
              <List dense>
                <ListItem>
                  <ListItemIcon>
                    {indexCheck.index_exists ? <CheckCircle color="success" /> : <ErrorIcon color="error" />}
                  </ListItemIcon>
                  <ListItemText
                    primary="FAISS Index"
                    secondary={`Size: ${indexCheck.index_size_mb?.toFixed(1)} MB`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    {indexCheck.metadata_exists ? <CheckCircle color="success" /> : <ErrorIcon color="error" />}
                  </ListItemIcon>
                  <ListItemText
                    primary="Metadata"
                    secondary={`Size: ${indexCheck.metadata_size_mb?.toFixed(1)} MB | Count: ${indexCheck.metadata_count || 0}`}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Last Modified"
                    secondary={indexCheck.last_modified ? new Date(indexCheck.last_modified).toLocaleString() : 'Unknown'}
                  />
                </ListItem>
                <ListItem>
                  <ListItemText
                    primary="Backup Status"
                    secondary={`${indexCheck.backup_count || 0} backups available`}
                  />
                </ListItem>
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
                Performance Metrics
              </Typography>
              
              <TableContainer component={Paper} variant="outlined">
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Metric</TableCell>
                      <TableCell align="right">Value</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    <TableRow>
                      <TableCell>Uptime</TableCell>
                      <TableCell align="right">
                        {performanceCheck.uptime_hours?.toFixed(1)} hours
                      </TableCell>
                      <TableCell>
                        <Chip label="Active" color="success" size="small" />
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Total Requests</TableCell>
                      <TableCell align="right">
                        {performanceCheck.total_requests?.toLocaleString() || 0}
                      </TableCell>
                      <TableCell>-</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Error Rate</TableCell>
                      <TableCell align="right">
                        {performanceCheck.error_rate_percent?.toFixed(2)}%
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={performanceCheck.error_rate_percent > 5 ? 'High' : 'Normal'}
                          color={performanceCheck.error_rate_percent > 5 ? 'error' : 'success'}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>Average Response Time</TableCell>
                      <TableCell align="right">
                        {performanceCheck.avg_response_time_ms?.toFixed(0)} ms
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={performanceCheck.avg_response_time_ms > 1000 ? 'Slow' : 'Fast'}
                          color={performanceCheck.avg_response_time_ms > 1000 ? 'warning' : 'success'}
                          size="small"
                        />
                      </TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell>P95 Response Time</TableCell>
                      <TableCell align="right">
                        {performanceCheck.p95_response_time_ms?.toFixed(0)} ms
                      </TableCell>
                      <TableCell>-</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Data Freshness */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <DataUsage sx={{ mr: 1, verticalAlign: 'middle' }} />
                Data Freshness
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Typography variant="body1">
                  Index Age: {dataCheck.index_age_hours?.toFixed(1)} hours
                </Typography>
                {dataCheck.needs_update && (
                  <Chip label="Update Recommended" color="warning" size="small" />
                )}
                <Typography variant="body2" color="text.secondary" ml="auto">
                  Last Update: {dataCheck.last_update ? new Date(dataCheck.last_update).toLocaleString() : 'Unknown'}
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default HealthMonitor