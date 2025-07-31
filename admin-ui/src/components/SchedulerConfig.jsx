import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Switch,
  FormControlLabel,
  TextField,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Paper,
  Divider
} from '@mui/material';
import {
  Schedule as ScheduleIcon,
  PlayArrow as PlayIcon,
  History as HistoryIcon,
  Refresh as RefreshIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Warning as WarningIcon,
  Timer as TimerIcon
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8008';

const SchedulerConfig = () => {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncStatus, setSyncStatus] = useState(null);
  const [syncHistory, setSyncHistory] = useState([]);
  const [editingJob, setEditingJob] = useState(null);
  const [showHistory, setShowHistory] = useState(false);
  
  // Form state for editing
  const [formData, setFormData] = useState({
    enabled: false,
    scheduleType: 'interval',
    intervalMinutes: 60,
    dailyTime: '00:00',
    cronExpression: '0 * * * *'
  });

  // Fetch scheduler jobs
  const fetchJobs = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API_BASE_URL}/scheduler/jobs`);
      setJobs(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch scheduler jobs');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch sync status
  const fetchSyncStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/sync/status`);
      setSyncStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch sync status:', err);
    }
  };

  // Fetch sync history
  const fetchSyncHistory = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/sync/history?limit=20`);
      setSyncHistory(response.data.history);
    } catch (err) {
      console.error('Failed to fetch sync history:', err);
    }
  };

  useEffect(() => {
    fetchJobs();
    fetchSyncStatus();
    fetchSyncHistory();
    
    // Refresh every 30 seconds
    const interval = setInterval(() => {
      fetchJobs();
      fetchSyncStatus();
    }, 30000);
    
    return () => clearInterval(interval);
  }, []);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (!editingJob) {
      // Reset form to defaults when dialog closes
      setFormData({
        enabled: false,
        scheduleType: 'interval',
        intervalMinutes: 60,
        dailyTime: '00:00',
        cronExpression: '0 * * * *'
      });
    }
  }, [editingJob]);

  // Handle job edit
  const handleEditJob = (job) => {
    console.log('Edit job called with:', job); // Debug log
    setEditingJob(job);
    
    // Parse schedule configuration with a slight delay to ensure dialog is ready
    setTimeout(() => {
      const schedule = job.schedule;
      console.log('Schedule config:', schedule); // Debug log
      
      const newFormData = {
        enabled: job.enabled,
        scheduleType: schedule.type || 'interval',
        intervalMinutes: schedule.interval_minutes || 60,
        dailyTime: schedule.time || '00:00',
        cronExpression: schedule.expression || '0 * * * *'
      };
      
      console.log('Setting form data:', newFormData); // Debug log
      setFormData(newFormData);
    }, 100);
  };

  // Handle form changes
  const handleFormChange = (field, value) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Save job configuration
  const handleSaveJob = async () => {
    try {
      const scheduleConfig = {
        type: formData.scheduleType
      };
      
      // Add type-specific fields
      if (formData.scheduleType === 'interval') {
        scheduleConfig.interval_minutes = formData.intervalMinutes;
      } else if (formData.scheduleType === 'daily') {
        scheduleConfig.time = formData.dailyTime;
      } else if (formData.scheduleType === 'cron') {
        scheduleConfig.expression = formData.cronExpression;
      }
      
      await axios.put(`${API_BASE_URL}/scheduler/jobs/${editingJob.id}`, {
        enabled: formData.enabled,
        schedule: scheduleConfig
      });
      
      setEditingJob(null);
      fetchJobs();
      setError(null);
    } catch (err) {
      setError('Failed to update job configuration');
      console.error(err);
    }
  };

  // Trigger manual sync
  const handleManualSync = async () => {
    try {
      await axios.post(`${API_BASE_URL}/sync/manual`);
      fetchJobs();
      fetchSyncStatus();
    } catch (err) {
      setError('Failed to trigger manual sync');
      console.error(err);
    }
  };

  // Get job status icon
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed':
        return <CheckIcon color="success" />;
      case 'running':
        return <CircularProgress size={20} />;
      case 'error':
        return <ErrorIcon color="error" />;
      default:
        return <TimerIcon color="action" />;
    }
  };

  // Format duration
  const formatDuration = (seconds) => {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" p={4}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        <ScheduleIcon sx={{ mr: 1, verticalAlign: 'bottom' }} />
        Scheduler Configuration
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Sync Status Card */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h6">Sync Status</Typography>
            <Box>
              <Tooltip title="Refresh">
                <IconButton onClick={() => { fetchJobs(); fetchSyncStatus(); }}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="View History">
                <IconButton onClick={() => setShowHistory(true)}>
                  <HistoryIcon />
                </IconButton>
              </Tooltip>
              <Button
                variant="contained"
                startIcon={<PlayIcon />}
                onClick={handleManualSync}
                sx={{ ml: 1 }}
              >
                Manual Sync
              </Button>
            </Box>
          </Box>

          {syncStatus && (
            <Grid container spacing={2}>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Last Sync
                </Typography>
                <Typography variant="body1">
                  {syncStatus.stats.last_sync 
                    ? format(parseISO(syncStatus.stats.last_sync), 'MMM d, yyyy HH:mm')
                    : 'Never'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Total Cases
                </Typography>
                <Typography variant="body1">
                  {syncStatus.stats.total_cases_in_index?.toLocaleString() || '0'}
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Average Sync Duration
                </Typography>
                <Typography variant="body1">
                  {formatDuration(syncStatus.stats.average_sync_duration_seconds)}
                </Typography>
              </Grid>
              <Grid item xs={12} md={3}>
                <Typography variant="body2" color="textSecondary">
                  Scheduler Status
                </Typography>
                <Chip
                  label={syncStatus.scheduler_running ? 'Running' : 'Stopped'}
                  color={syncStatus.scheduler_running ? 'success' : 'error'}
                  size="small"
                />
              </Grid>
            </Grid>
          )}

          {/* Validation Warnings */}
          {syncStatus?.validation?.warnings?.length > 0 && (
            <Box mt={2}>
              {syncStatus.validation.warnings.map((warning, idx) => (
                <Alert key={idx} severity="warning" sx={{ mb: 1 }}>
                  {warning}
                </Alert>
              ))}
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Scheduled Jobs */}
      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Scheduled Jobs
          </Typography>

          <List>
            {jobs.map((job) => (
              <React.Fragment key={job.id}>
                <ListItem>
                  <Box display="flex" alignItems="center" width="100%">
                    <Box mr={2}>
                      {getStatusIcon(job.status)}
                    </Box>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center">
                          <Typography variant="subtitle1">
                            {job.name}
                          </Typography>
                          <Chip
                            label={job.enabled ? 'Enabled' : 'Disabled'}
                            color={job.enabled ? 'success' : 'default'}
                            size="small"
                            sx={{ ml: 1 }}
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="textSecondary">
                            {job.description}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Schedule: {job.schedule.type === 'interval' 
                              ? `Every ${job.schedule.interval_minutes} minutes`
                              : job.schedule.type === 'daily'
                              ? `Daily at ${job.schedule.time}`
                              : job.schedule.expression}
                          </Typography>
                          {job.last_run && (
                            <Typography variant="body2" color="textSecondary">
                              Last run: {format(parseISO(job.last_run), 'MMM d, yyyy HH:mm')}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                    <ListItemSecondaryAction>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => handleEditJob(job)}
                      >
                        Configure
                      </Button>
                    </ListItemSecondaryAction>
                  </Box>
                </ListItem>
                <Divider />
              </React.Fragment>
            ))}
          </List>
        </CardContent>
      </Card>

      {/* Edit Job Dialog */}
      <Dialog open={!!editingJob} onClose={() => setEditingJob(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Configure {editingJob?.name}</DialogTitle>
        <DialogContent>
          <Box py={2}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.enabled}
                  onChange={(e) => handleFormChange('enabled', e.target.checked)}
                />
              }
              label="Enable Schedule"
              sx={{ mb: 2 }}
            />

            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Schedule Type</InputLabel>
              <Select
                value={formData.scheduleType}
                onChange={(e) => handleFormChange('scheduleType', e.target.value)}
                disabled={!formData.enabled}
              >
                <MenuItem value="interval">Interval</MenuItem>
                <MenuItem value="daily">Daily</MenuItem>
                <MenuItem value="cron">Cron Expression</MenuItem>
              </Select>
            </FormControl>

            {formData.scheduleType === 'interval' && (
              <TextField
                key={`interval-${editingJob?.id}`}
                fullWidth
                label="Interval (minutes)"
                type="number"
                value={formData.intervalMinutes || ''}
                onChange={(e) => {
                  const value = e.target.value === '' ? 60 : parseInt(e.target.value) || 60;
                  handleFormChange('intervalMinutes', value);
                }}
                disabled={!formData.enabled}
                inputProps={{ min: 1, max: 1440 }}
                helperText="How often to run the sync (1-1440 minutes)"
                placeholder="60"
              />
            )}

            {formData.scheduleType === 'daily' && (
              <TextField
                fullWidth
                label="Time"
                type="time"
                value={formData.dailyTime}
                onChange={(e) => handleFormChange('dailyTime', e.target.value)}
                disabled={!formData.enabled}
                helperText="What time to run the daily sync"
              />
            )}

            {formData.scheduleType === 'cron' && (
              <TextField
                fullWidth
                label="Cron Expression"
                value={formData.cronExpression}
                onChange={(e) => handleFormChange('cronExpression', e.target.value)}
                disabled={!formData.enabled}
                helperText="Cron expression (e.g., 0 */2 * * * for every 2 hours)"
              />
            )}
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditingJob(null)}>Cancel</Button>
          <Button onClick={handleSaveJob} variant="contained">Save</Button>
        </DialogActions>
      </Dialog>

      {/* Sync History Dialog */}
      <Dialog open={showHistory} onClose={() => setShowHistory(false)} maxWidth="md" fullWidth>
        <DialogTitle>Sync History</DialogTitle>
        <DialogContent>
          <List>
            {syncHistory.map((entry, idx) => (
              <ListItem key={idx}>
                <ListItemText
                  primary={format(parseISO(entry.timestamp), 'MMM d, yyyy HH:mm')}
                  secondary={
                    <Box>
                      <Typography variant="body2">
                        Cases processed: {entry.cases_processed} | 
                        Added: {entry.cases_added} | 
                        Duration: {formatDuration(entry.duration_seconds)}
                      </Typography>
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHistory(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SchedulerConfig;