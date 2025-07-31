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
  LinearProgress,
} from '@mui/material'
import {
  DataUsage,
  FilterList,
  CleaningServices,
  Assessment,
  Refresh,
} from '@mui/icons-material'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts'

// Mock data for data quality metrics (would come from backend in real implementation)
const mockQualityData = {
  totalRecords: 2547,
  processedRecords: 2489,
  filteredRecords: 58,
  duplicatesFound: 23,
  validationErrors: 12,
  qualityScore: 97.7,
  filters: {
    textLength: { applied: 2547, filtered: 15 },
    repetitionScore: { applied: 2547, filtered: 8 },
    specialCharacters: { applied: 2547, filtered: 18 },
    numericContent: { applied: 2547, filtered: 12 },
    wordCount: { applied: 2547, filtered: 5 },
  },
  fieldStats: [
    { field: 'Subject_Description', completeness: 98.5, avgLength: 42 },
    { field: 'Issue_Plain_Text', completeness: 95.2, avgLength: 156 },
    { field: 'Resolution_Plain_Text', completeness: 87.3, avgLength: 203 },
    { field: 'Case_Number', completeness: 100, avgLength: 12 },
    { field: 'Status_Text', completeness: 99.8, avgLength: 8 },
  ],
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

function DataQuality() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [qualityData, setQualityData] = useState(mockQualityData)
  const [refreshing, setRefreshing] = useState(false)

  const fetchQualityData = async () => {
    try {
      setRefreshing(true)
      // Simulate API call
      await new Promise(resolve => setTimeout(resolve, 1000))
      // In real implementation, this would fetch from /api/quality/stats
      setQualityData(mockQualityData)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchQualityData()
  }, [])

  const getQualityColor = (score) => {
    if (score >= 95) return 'success'
    if (score >= 85) return 'warning'
    return 'error'
  }

  const getCompletenessColor = (completeness) => {
    if (completeness >= 95) return 'success'
    if (completeness >= 85) return 'warning'
    return 'error'
  }

  // Prepare chart data
  const filterData = Object.entries(qualityData.filters).map(([name, data]) => ({
    name: name.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase()),
    filtered: data.filtered,
    passed: data.applied - data.filtered,
  }))

  const qualityDistribution = [
    { name: 'High Quality', value: qualityData.processedRecords - 50, color: COLORS[0] },
    { name: 'Medium Quality', value: 35, color: COLORS[1] },
    { name: 'Low Quality', value: 15, color: COLORS[2] },
    { name: 'Filtered Out', value: qualityData.filteredRecords, color: COLORS[3] },
  ]

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="80vh">
        <CircularProgress />
      </Box>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Data Quality Dashboard</Typography>
        <Button
          variant="outlined"
          startIcon={refreshing ? <CircularProgress size={20} /> : <Refresh />}
          onClick={fetchQualityData}
          disabled={refreshing}
        >
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </Button>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error loading data quality metrics: {error}
        </Alert>
      )}

      <Grid container spacing={3}>
        {/* Quality Overview */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Assessment sx={{ mr: 1, verticalAlign: 'middle' }} />
                Data Quality Overview
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={2}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {qualityData.totalRecords.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Records
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      {qualityData.processedRecords.toLocaleString()}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Processed
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="warning.main">
                      {qualityData.filteredRecords}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Filtered Out
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      {qualityData.duplicatesFound}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Duplicates Found
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="error.main">
                      {qualityData.validationErrors}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Validation Errors
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={2}>
                  <Box textAlign="center">
                    <Typography 
                      variant="h4" 
                      color={`${getQualityColor(qualityData.qualityScore)}.main`}
                    >
                      {qualityData.qualityScore}%
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Quality Score
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Quality Distribution Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Data Quality Distribution
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={qualityDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {qualityDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Filter Performance Chart */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Quality Filter Performance
              </Typography>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={filterData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="passed" stackId="a" fill="#4caf50" name="Passed" />
                  <Bar dataKey="filtered" stackId="a" fill="#f44336" name="Filtered" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Field Completeness */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <DataUsage sx={{ mr: 1, verticalAlign: 'middle' }} />
                Field Completeness & Statistics
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Field Name</TableCell>
                      <TableCell align="right">Completeness</TableCell>
                      <TableCell align="right">Average Length</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>Progress</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {qualityData.fieldStats.map((field) => (
                      <TableRow key={field.field}>
                        <TableCell component="th" scope="row">
                          {field.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </TableCell>
                        <TableCell align="right">
                          {field.completeness.toFixed(1)}%
                        </TableCell>
                        <TableCell align="right">
                          {field.avgLength} chars
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={field.completeness >= 95 ? 'Excellent' : 
                                   field.completeness >= 85 ? 'Good' : 'Needs Attention'}
                            color={getCompletenessColor(field.completeness)}
                            size="small"
                          />
                        </TableCell>
                        <TableCell>
                          <Box display="flex" alignItems="center" gap={1}>
                            <LinearProgress
                              variant="determinate"
                              value={field.completeness}
                              sx={{ width: 100 }}
                              color={getCompletenessColor(field.completeness)}
                            />
                            <Typography variant="body2" color="text.secondary">
                              {field.completeness.toFixed(0)}%
                            </Typography>
                          </Box>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Quality Filters Details */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <FilterList sx={{ mr: 1, verticalAlign: 'middle' }} />
                Quality Filter Details
              </Typography>
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Filter Type</TableCell>
                      <TableCell align="right">Records Processed</TableCell>
                      <TableCell align="right">Records Filtered</TableCell>
                      <TableCell align="right">Filter Rate</TableCell>
                      <TableCell>Status</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {Object.entries(qualityData.filters).map(([filterName, data]) => {
                      const filterRate = (data.filtered / data.applied) * 100
                      return (
                        <TableRow key={filterName}>
                          <TableCell component="th" scope="row">
                            {filterName.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                          </TableCell>
                          <TableCell align="right">
                            {data.applied.toLocaleString()}
                          </TableCell>
                          <TableCell align="right">
                            {data.filtered}
                          </TableCell>
                          <TableCell align="right">
                            {filterRate.toFixed(2)}%
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={filterRate < 2 ? 'Effective' : filterRate < 5 ? 'Normal' : 'High'}
                              color={filterRate < 2 ? 'success' : filterRate < 5 ? 'info' : 'warning'}
                              size="small"
                            />
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Grid>

        {/* Data Quality Actions */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <CleaningServices sx={{ mr: 1, verticalAlign: 'middle' }} />
                Data Quality Actions
              </Typography>
              <Box display="flex" gap={2} flexWrap="wrap">
                <Button
                  variant="outlined"
                  startIcon={<FilterList />}
                  onClick={() => alert('Reprocess data filters - Feature coming soon!')}
                >
                  Reprocess Filters
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<CleaningServices />}
                  onClick={() => alert('Run data cleanup - Feature coming soon!')}
                >
                  Run Data Cleanup
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Assessment />}
                  onClick={() => alert('Generate quality report - Feature coming soon!')}
                >
                  Generate Report
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default DataQuality