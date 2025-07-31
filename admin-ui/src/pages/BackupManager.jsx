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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Chip,
} from '@mui/material'
import {
  Backup,
  Restore,
  Delete,
  Add,
  Refresh,
  Download,
  Info,
} from '@mui/icons-material'
import { backupAPI } from '../services/api'

function BackupManager() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [backups, setBackups] = useState([])
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false)
  const [selectedBackup, setSelectedBackup] = useState(null)
  const [backupDescription, setBackupDescription] = useState('')
  const [processing, setProcessing] = useState(false)

  useEffect(() => {
    fetchBackups()
  }, [])

  const fetchBackups = async () => {
    try {
      setLoading(true)
      const response = await backupAPI.listBackups()
      setBackups(response.data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateBackup = async () => {
    try {
      setProcessing(true)
      await backupAPI.createBackup(backupDescription)
      setCreateDialogOpen(false)
      setBackupDescription('')
      await fetchBackups()
      alert('Backup created successfully!')
    } catch (err) {
      alert('Error creating backup: ' + err.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleRestoreBackup = async () => {
    try {
      setProcessing(true)
      await backupAPI.restoreBackup(selectedBackup.id)
      setRestoreDialogOpen(false)
      setSelectedBackup(null)
      alert('Backup restored successfully!')
    } catch (err) {
      alert('Error restoring backup: ' + err.message)
    } finally {
      setProcessing(false)
    }
  }

  const handleDeleteBackup = async (backupId) => {
    if (window.confirm('Are you sure you want to delete this backup?')) {
      try {
        await backupAPI.deleteBackup(backupId)
        await fetchBackups()
        alert('Backup deleted successfully!')
      } catch (err) {
        alert('Error deleting backup: ' + err.message)
      }
    }
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString()
  }

  const formatSize = (sizeInMB) => {
    if (sizeInMB < 1024) return `${sizeInMB.toFixed(1)} MB`
    return `${(sizeInMB / 1024).toFixed(2)} GB`
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
        Error loading backups: {error}
      </Alert>
    )
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4">Backup Manager</Typography>
        <Box gap={2} display="flex">
          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={fetchBackups}
          >
            Refresh
          </Button>
          <Button
            variant="contained"
            startIcon={<Add />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Backup
          </Button>
        </Box>
      </Box>

      <Grid container spacing={3}>
        {/* Backup Statistics */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                <Backup sx={{ mr: 1, verticalAlign: 'middle' }} />
                Backup Statistics
              </Typography>
              <Grid container spacing={3}>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="primary">
                      {backups.length}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Backups
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="success.main">
                      {backups.length > 0 ? formatDate(backups[0].timestamp) : 'None'}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Latest Backup
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="info.main">
                      {formatSize(backups.reduce((sum, b) => sum + b.index_size_mb + b.metadata_size_mb, 0))}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Total Size
                    </Typography>
                  </Box>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Box textAlign="center">
                    <Typography variant="h4" color="warning.main">
                      5
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Max Backups
                    </Typography>
                  </Box>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Backup List */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Available Backups
              </Typography>
              {backups.length === 0 ? (
                <Box textAlign="center" py={4}>
                  <Typography variant="body1" color="text.secondary">
                    No backups available. Create your first backup to get started.
                  </Typography>
                </Box>
              ) : (
                <TableContainer component={Paper} variant="outlined">
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Backup ID</TableCell>
                        <TableCell>Created</TableCell>
                        <TableCell>Description</TableCell>
                        <TableCell align="right">Index Size</TableCell>
                        <TableCell align="right">Metadata Size</TableCell>
                        <TableCell align="center">Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {backups.map((backup) => (
                        <TableRow key={backup.id}>
                          <TableCell>
                            <Box display="flex" alignItems="center" gap={1}>
                              <Typography variant="body2" fontFamily="monospace">
                                {backup.id}
                              </Typography>
                              {backup.id === backups[0]?.id && (
                                <Chip label="Latest" color="primary" size="small" />
                              )}
                            </Box>
                          </TableCell>
                          <TableCell>
                            {formatDate(backup.timestamp)}
                          </TableCell>
                          <TableCell>
                            {backup.description || 'No description'}
                          </TableCell>
                          <TableCell align="right">
                            {formatSize(backup.index_size_mb)}
                          </TableCell>
                          <TableCell align="right">
                            {formatSize(backup.metadata_size_mb)}
                          </TableCell>
                          <TableCell align="center">
                            <Box display="flex" gap={1} justifyContent="center">
                              <IconButton
                                size="small"
                                color="primary"
                                onClick={() => {
                                  setSelectedBackup(backup)
                                  setRestoreDialogOpen(true)
                                }}
                                title="Restore Backup"
                              >
                                <Restore />
                              </IconButton>
                              <IconButton
                                size="small"
                                color="info"
                                title="Backup Info"
                              >
                                <Info />
                              </IconButton>
                              <IconButton
                                size="small"
                                color="error"
                                onClick={() => handleDeleteBackup(backup.id)}
                                title="Delete Backup"
                              >
                                <Delete />
                              </IconButton>
                            </Box>
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
      </Grid>

      {/* Create Backup Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Backup</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Description (optional)"
            fullWidth
            variant="outlined"
            value={backupDescription}
            onChange={(e) => setBackupDescription(e.target.value)}
            placeholder="e.g., Before major update, Weekly backup, etc."
            sx={{ mt: 2 }}
          />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            This will create a backup of the current FAISS index and metadata files.
            The backup will be automatically timestamped and stored securely.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleCreateBackup}
            variant="contained"
            disabled={processing}
            startIcon={processing ? <CircularProgress size={20} /> : <Backup />}
          >
            {processing ? 'Creating...' : 'Create Backup'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Restore Backup Dialog */}
      <Dialog open={restoreDialogOpen} onClose={() => setRestoreDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Restore Backup</DialogTitle>
        <DialogContent>
          <Typography variant="body1" gutterBottom>
            Are you sure you want to restore the following backup?
          </Typography>
          {selectedBackup && (
            <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.100', borderRadius: 1 }}>
              <Typography variant="body2">
                <strong>Backup ID:</strong> {selectedBackup.id}
              </Typography>
              <Typography variant="body2">
                <strong>Created:</strong> {formatDate(selectedBackup.timestamp)}
              </Typography>
              <Typography variant="body2">
                <strong>Description:</strong> {selectedBackup.description || 'No description'}
              </Typography>
              <Typography variant="body2">
                <strong>Size:</strong> {formatSize(selectedBackup.index_size_mb + selectedBackup.metadata_size_mb)}
              </Typography>
            </Box>
          )}
          <Alert severity="warning" sx={{ mt: 2 }}>
            <Typography variant="body2">
              <strong>Warning:</strong> This will replace the current index and metadata with the backup data.
              A backup of the current state will be created automatically before restoring.
            </Typography>
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestoreDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={handleRestoreBackup}
            variant="contained"
            color="warning"
            disabled={processing}
            startIcon={processing ? <CircularProgress size={20} /> : <Restore />}
          >
            {processing ? 'Restoring...' : 'Restore Backup'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default BackupManager