import React, { useState } from 'react'
import {
  Box,
  Card,
  CardContent,
  Grid,
  Typography,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Slider,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material'
import {
  Search,
  ExpandMore,
  QueryStats,
  AccessTime,
  TrendingUp,
} from '@mui/icons-material'
import { vectorAPI } from '../services/api'

function SearchTest() {
  const [query, setQuery] = useState('')
  const [topK, setTopK] = useState(10)
  const [threshold, setThreshold] = useState(0.4)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [searchTime, setSearchTime] = useState(0)
  const [searchHistory, setSearchHistory] = useState([])

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a search query')
      return
    }

    try {
      setLoading(true)
      setError(null)
      const startTime = Date.now()
      
      const response = await vectorAPI.search(query, topK, threshold)
      const endTime = Date.now()
      const responseTime = endTime - startTime
      
      setResults(response.data)
      setSearchTime(responseTime)
      
      // Add to search history
      const historyEntry = {
        id: Date.now(),
        query: query,
        timestamp: new Date().toLocaleString(),
        resultCount: response.data.results.length,
        searchTime: responseTime,
        topK,
        threshold,
      }
      setSearchHistory(prev => [historyEntry, ...prev.slice(0, 9)]) // Keep last 10 searches
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (event) => {
    if (event.key === 'Enter') {
      handleSearch()
    }
  }

  const getSimilarityColor = (score) => {
    if (score >= 0.8) return 'success'
    if (score >= 0.6) return 'info'
    if (score >= 0.4) return 'warning'
    return 'default'
  }

  const getSimilarityLabel = (score) => {
    if (score >= 0.8) return 'High'
    if (score >= 0.6) return 'Medium'
    if (score >= 0.4) return 'Low'
    return 'Very Low'
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Search Test Interface
      </Typography>

      <Grid container spacing={3}>
        {/* Search Interface */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Search sx={{ mr: 1, verticalAlign: 'middle' }} />
                Vector Similarity Search
              </Typography>
              
              <Box mb={3}>
                <TextField
                  fullWidth
                  label="Search Query"
                  variant="outlined"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Enter your search query (e.g., 'server crashes unexpectedly')"
                  multiline
                  minRows={2}
                  maxRows={4}
                />
              </Box>

              <Grid container spacing={3} mb={3}>
                <Grid item xs={12} md={6}>
                  <Typography gutterBottom>
                    Number of Results (Top K): {topK}
                  </Typography>
                  <Slider
                    value={topK}
                    onChange={(e, newValue) => setTopK(newValue)}
                    min={1}
                    max={50}
                    marks={[
                      { value: 5, label: '5' },
                      { value: 10, label: '10' },
                      { value: 25, label: '25' },
                      { value: 50, label: '50' },
                    ]}
                    valueLabelDisplay="auto"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography gutterBottom>
                    Similarity Threshold: {threshold}
                  </Typography>
                  <Slider
                    value={threshold}
                    onChange={(e, newValue) => setThreshold(newValue)}
                    min={0.1}
                    max={1.0}
                    step={0.05}
                    marks={[
                      { value: 0.1, label: '0.1' },
                      { value: 0.4, label: '0.4' },
                      { value: 0.7, label: '0.7' },
                      { value: 1.0, label: '1.0' },
                    ]}
                    valueLabelDisplay="auto"
                  />
                </Grid>
              </Grid>

              <Button
                variant="contained"
                size="large"
                startIcon={loading ? <CircularProgress size={20} /> : <Search />}
                onClick={handleSearch}
                disabled={loading || !query.trim()}
                fullWidth
              >
                {loading ? 'Searching...' : 'Search Cases'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Error Display */}
        {error && (
          <Grid item xs={12}>
            <Alert severity="error">
              Search Error: {error}
            </Alert>
          </Grid>
        )}

        {/* Search Results */}
        {results && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                  <Typography variant="h6">
                    Search Results ({results.total_results} found)
                  </Typography>
                  <Box display="flex" gap={2} alignItems="center">
                    <Chip
                      icon={<QueryStats />}
                      label={`Query: "${results.query}"`}
                      variant="outlined"
                    />
                    <Chip
                      icon={<AccessTime />}
                      label={`${results.search_time_ms}ms`}
                      color="primary"
                    />
                  </Box>
                </Box>

                {results.results.length === 0 ? (
                  <Box textAlign="center" py={4}>
                    <Typography variant="body1" color="text.secondary">
                      No results found matching your query and similarity threshold.
                      Try lowering the similarity threshold or using different keywords.
                    </Typography>
                  </Box>
                ) : (
                  <TableContainer component={Paper} variant="outlined">
                    <Table>
                      <TableHead>
                        <TableRow>
                          <TableCell>Similarity</TableCell>
                          <TableCell>Case Number</TableCell>
                          <TableCell>Subject Description</TableCell>
                          <TableCell>Status Text</TableCell>
                          <TableCell>Issue Plain Text</TableCell>
                          <TableCell>Resolution Text</TableCell>
                          <TableCell>Preview</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {results.results.map((result, index) => (
                          <TableRow key={result.case_id || index}>
                            <TableCell>
                              <Box display="flex" alignItems="center" gap={1}>
                                <Typography variant="body2" fontWeight="bold">
                                  {(result.similarity_score * 100).toFixed(1)}%
                                </Typography>
                                <Chip
                                  label={getSimilarityLabel(result.similarity_score)}
                                  color={getSimilarityColor(result.similarity_score)}
                                  size="small"
                                />
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" fontFamily="monospace">
                                {result.case_number || 'N/A'}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2">
                                {result.subject_description || 'No subject description'}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Chip
                                label={result.status_text || 'Unknown'}
                                size="small"
                                variant="outlined"
                              />
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {result.issue_plain_text || 'N/A'}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                {result.resolution_plain_text || 'N/A'}
                              </Typography>
                            </TableCell>
                            <TableCell>
                              <Accordion>
                                <AccordionSummary expandIcon={<ExpandMore />}>
                                  <Typography variant="body2">
                                    {result.preview_text?.substring(0, 50)}...
                                  </Typography>
                                </AccordionSummary>
                                <AccordionDetails>
                                  <Typography variant="body2">
                                    {result.preview_text || 'No preview available'}
                                  </Typography>
                                </AccordionDetails>
                              </Accordion>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Search History */}
        {searchHistory.length > 0 && (
          <Grid item xs={12}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  <TrendingUp sx={{ mr: 1, verticalAlign: 'middle' }} />
                  Search History
                </Typography>
                <TableContainer component={Paper} variant="outlined">
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>Query</TableCell>
                        <TableCell>Timestamp</TableCell>
                        <TableCell align="right">Results</TableCell>
                        <TableCell align="right">Response Time</TableCell>
                        <TableCell align="right">Top K</TableCell>
                        <TableCell align="right">Threshold</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {searchHistory.map((entry) => (
                        <TableRow key={entry.id}>
                          <TableCell>
                            <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>
                              {entry.query}
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2">
                              {entry.timestamp}
                            </Typography>
                          </TableCell>
                          <TableCell align="right">{entry.resultCount}</TableCell>
                          <TableCell align="right">{entry.searchTime}ms</TableCell>
                          <TableCell align="right">{entry.topK}</TableCell>
                          <TableCell align="right">{entry.threshold}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              </CardContent>
            </Card>
          </Grid>
        )}

        {/* Sample Queries */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Sample Queries
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                Try these sample queries to test the search functionality:
              </Typography>
              <Box display="flex" flexWrap="wrap" gap={1}>
                {[
                  'server crashes unexpectedly',
                  'application performance issues',
                  'database connection timeout',
                  'memory leak error',
                  'network connectivity problems',
                  'authentication failure',
                  'backup and restore',
                  'configuration error',
                ].map((sampleQuery) => (
                  <Chip
                    key={sampleQuery}
                    label={sampleQuery}
                    onClick={() => setQuery(sampleQuery)}
                    clickable
                    variant="outlined"
                    size="small"
                  />
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  )
}

export default SearchTest