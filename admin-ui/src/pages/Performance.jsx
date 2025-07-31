import React, { useState, useEffect } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import {
  Refresh,
  Save,
  TrendingUp,
  Speed,
  Timeline,
} from '@mui/icons-material'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import { performanceAPI } from '../services/api'

function Performance() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [report, setReport] = useState(null)
  const [operationStats, setOperationStats] = useState(null)
  const [batchPerformance, setBatchPerformance] = useState(null)
  const [recommendations, setRecommendations] = useState([])

  useEffect(() => {
    fetchPerformanceData()
  }, [])

  const fetchPerformanceData = async () => {
    try {
      setLoading(true)
      const [reportRes, operationsRes, batchRes, recRes] = await Promise.all([
        performanceAPI.getReport(),
        performanceAPI.getOperationStats(),
        performanceAPI.getBatchPerformance(),
        performanceAPI.getRecommendations(),
      ])
      
      setReport(reportRes.data)
      setOperationStats(operationsRes.data)
      setBatchPerformance(batchRes.data)
      setRecommendations(recRes.data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveMetrics = async () => {
    try {
      await performanceAPI.saveMetrics()
      alert('Metrics saved successfully!')
    } catch (err) {
      alert('Error saving metrics: ' + err.message)
    }
  }

  const formatResponseTime = (ms) => {
    if (ms < 1000) return `${ms.toFixed(0)}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  const getPerformanceColor = (value, threshold) => {
    if (value > threshold) return 'error'
    if (value > threshold * 0.8) return 'warning'
    return 'success'
  }

  // Prepare chart data
  const operationsChartData = Object.entries(operationStats || {}).map(([name, stats]) => ({
    name: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
    avgTime: stats.avg_time_ms || 0,
    count: stats.count || 0,
    errorRate: (stats.error_rate || 0) * 100,
  }))

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
        Error loading performance data: {error}
      </Alert>
    )
  }

  const systemPerf = report?.system_performance || {}

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Performance Analytics</Typography>
        <Box gap={2} display="flex">
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchPerformanceData}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Save />}
            onClick={handleSaveMetrics}
          >
            Save Metrics
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Performance Overview */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
                Performance Overview
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {systemPerf.total_operations || 0}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Operations
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="error">
                      {((systemPerf.overall_error_rate || 0) * 100).toFixed(2)}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Error Rate
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      {formatResponseTime(systemPerf.avg_response_time_ms || 0)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Avg Response Time
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      {formatResponseTime(systemPerf.median_response_time_ms || 0)}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Median Response Time
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Operation Performance Chart */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Operation Performance
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={operationsChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip formatter={(value, name) => [
                    name === 'avgTime' ? formatResponseTime(value) : 
                    name === 'errorRate' ? `${value.toFixed(2)}%` : value,
                    name === 'avgTime' ? 'Avg Time' :
                    name === 'errorRate' ? 'Error Rate' : 'Count'
                  ]} />
                  <Legend />
                  <Bar dataKey="avgTime" fill="#1976d2" name="Avg Time (ms)" />
                  <Bar dataKey="count" fill="#2e7d32" name="Count" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Performance Recommendations */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Optimization Recommendations
              </Typography>
              {recommendations.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  No recommendations at this time. System is performing well!
                </Typography>
              ) : (
                <List dense>
                  {recommendations.map((rec, index) => (
                    <ListItem key={index}>
                      <ListItemText
                        primary={rec.message}
                        secondary={`Operation: ${rec.operation}`}
                      />
                      <Chip
                        label={rec.severity}
                        color={rec.severity === 'high' ? 'error' : 'warning'}
                        size="small"
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Detailed Operation Statistics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Speed sx={{ mr: 1, verticalAlign: 'middle' }} />
                Detailed Operation Statistics
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Operation</TableCell>
                      <TableCell align="right">Count</TableCell>
                      <TableCell align="right">Errors</TableCell>
                      <TableCell align="right">Error Rate</TableCell>
                      <TableCell align="right">Avg Time</TableCell>
                      <TableCell align="right">Min Time</TableCell>
                      <TableCell align="right">Max Time</TableCell>
                      <TableCell align="right">P95 Time</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(operationStats || {}).map(([name, stats]) => (
                      <TableRow key={name}>
                        <TableCell component="th" scope="row">
                          {name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </TableCell>
                        <TableCell align="right">{stats.count || 0}</TableCell>
                        <TableCell align="right">{stats.errors || 0}</TableCell>
                        <TableCell align="right">
                          <Chip
                            label={`${((stats.error_rate || 0) * 100).toFixed(2)}%`}
                            color={getPerformanceColor((stats.error_rate || 0) * 100, 5)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell align="right">
                          {formatResponseTime(stats.avg_time_ms || 0)}
                        </TableCell>
                        <TableCell align="right">
                          {formatResponseTime(stats.min_time_ms || 0)}
                        </TableCell>
                        <TableCell align="right">
                          {formatResponseTime(stats.max_time_ms || 0)}
                        </TableCell>
                        <TableCell align="right">
                          {formatResponseTime(stats.p95_time_ms || 0)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Batch Processing Performance */}
        {Object.keys(batchPerformance || {}).length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <Timeline sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Batch Processing Performance
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Operation Type</TableCell>
                        <TableCell align="right">Batch Count</TableCell>
                        <TableCell align="right">Total Records</TableCell>
                        <TableCell align="right">Avg Throughput</TableCell>
                        <TableCell align="right">Max Throughput</TableCell>
                        <TableCell align="right">Success Rate</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {Object.entries(batchPerformance).map(([type, stats]) => (
                        <TableRow key={type}>
                          <TableCell component="th" scope="row">
                            {type.charAt(0).toUpperCase() + type.slice(1)}
                          </TableCell>
                          <TableCell align="right">{stats.batch_count || 0}</TableCell>
                          <TableCell align="right">{(stats.total_records || 0).toLocaleString()}</TableCell>
                          <TableCell align="right">
                            {(stats.avg_throughput_per_sec || 0).toFixed(1)} rec/sec
                          </TableCell>
                          <TableCell align="right">
                            {(stats.max_throughput_per_sec || 0).toFixed(1)} rec/sec
                          </TableCell>
                          <TableCell align="right">
                            <Chip
                              label={`${((stats.avg_success_rate || 0) * 100).toFixed(1)}%`}
                              color={getPerformanceColor((1 - (stats.avg_success_rate || 1)) * 100, 5)}
                              size="small"
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        )}
      </Grid>
    </Box>
  )
}

export default Performance