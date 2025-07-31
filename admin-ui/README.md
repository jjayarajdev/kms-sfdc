# KMS-SFDC Admin UI

A React-based admin dashboard for managing the KMS-SFDC Vector Database system.

## Features

### 📊 Dashboard
- Real-time system status monitoring
- Vector database statistics
- Performance metrics overview
- Quick health indicators

### 🏥 Health Monitor
- System resource monitoring (CPU, Memory, Disk)
- FAISS index health checks
- Performance metrics tracking
- Alert management with configurable thresholds

### ⚡ Performance Analytics
- Operation performance tracking
- Response time statistics
- Batch processing metrics
- Optimization recommendations
- Interactive charts and visualizations

### 💾 Backup Manager
- Create and restore backups
- Backup history and management
- Automated backup scheduling
- Version control and rollback

### 🔍 Search Test Interface
- Interactive search testing
- Adjustable similarity thresholds
- Search history tracking
- Sample queries for testing

### 🧹 Data Quality Dashboard
- Data validation metrics
- Field completeness analysis
- Quality filter performance
- Duplicate detection statistics

## Technology Stack

- **Frontend**: React 18, Material-UI 5
- **Charts**: Recharts for data visualization
- **HTTP Client**: Axios for API communication
- **Routing**: React Router v6
- **Build Tool**: Vite for fast development

## Getting Started

### Prerequisites
- Node.js 16+ and npm
- KMS-SFDC API server running on port 8008

### Installation

1. Navigate to admin UI directory:
   ```bash
   cd admin-ui
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

4. Open browser to http://localhost:4001

### Build for Production

```bash
npm run build
npm run preview
```

## API Integration

The admin UI connects to the KMS-SFDC API server via proxy configuration:
- Development: `http://localhost:8008` (proxied via Vite)
- API endpoints are automatically prefixed with `/api`

## Available Scripts

- `npm run dev` - Start development server on port 4001
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run start` - Alias for dev command

## Features Overview

### Real-time Monitoring
- System health status with color-coded indicators
- CPU, memory, and disk usage monitoring
- Vector database statistics and metrics
- Automatic refresh every 30-60 seconds

### Interactive Search
- Test vector similarity search functionality
- Adjustable parameters (top-k, similarity threshold)
- Real-time search results with similarity scores
- Search history and performance tracking

### Backup Management
- Create timestamped backups with descriptions
- View backup history and sizes
- Restore previous backups with safety confirmations
- Automatic backup retention (keeps last 5)

### Performance Insights
- Operation-level performance statistics
- Response time percentiles (P95, P99)
- Batch processing throughput analysis
- Optimization recommendations

### Data Quality Monitoring
- Field completeness and validation metrics
- Duplicate detection statistics
- Quality filter performance analysis
- Data distribution visualizations

## Configuration

The UI automatically adapts to the backend API configuration. Key settings:

- **Port**: 4001 (configurable in package.json and vite.config.js)
- **API Proxy**: Points to localhost:8008 by default
- **Refresh Intervals**: 30s for dashboard, 60s for health monitoring
- **Chart Colors**: Consistent Material-UI theme colors

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Security

- No authentication implemented (suitable for internal/admin use)
- CORS enabled for development
- API endpoints proxied to prevent direct exposure

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure KMS-SFDC API server is running on port 8008
   - Check proxy configuration in vite.config.js

2. **Charts Not Rendering**
   - Verify Recharts dependency is installed
   - Check browser console for JavaScript errors

3. **Port 4001 Already in Use**
   - Change port in package.json scripts
   - Update vite.config.js server port

### Development Tips

- Use browser dev tools Network tab to debug API calls
- Check browser console for React warnings/errors
- Enable React DevTools extension for component debugging