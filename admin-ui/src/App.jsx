import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Box } from '@mui/material'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import HealthMonitor from './pages/HealthMonitor'
import Performance from './pages/Performance'
import BackupManager from './pages/BackupManager'
import SearchTest from './pages/SearchTest'
import DataQuality from './pages/DataQuality'
import SchedulerConfig from './components/SchedulerConfig'

function App() {
  return (
    <Box sx={{ display: 'flex' }}>
      <Sidebar />
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/health" element={<HealthMonitor />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/scheduler" element={<SchedulerConfig />} />
          <Route path="/backup" element={<BackupManager />} />
          <Route path="/search" element={<SearchTest />} />
          <Route path="/quality" element={<DataQuality />} />
        </Routes>
      </Box>
    </Box>
  )
}

export default App