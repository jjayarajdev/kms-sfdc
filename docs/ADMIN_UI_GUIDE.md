# KMS-SFDC Admin UI - Complete Guide

## 🚀 Quick Start

The KMS-SFDC Admin UI is now running on **http://localhost:4001**

### Starting the Services

```bash
# Option 1: Start both API and Admin UI together
make start-all

# Option 2: Start services separately
make run-api          # API server on port 8008
make admin-ui-dev     # Admin UI on port 4001

# Option 3: Manual startup
cd admin-ui && npm run dev
```

## 📱 Admin UI Features

### 1. 📊 **Dashboard** (`/dashboard`)
- **System Status**: Real-time health indicators
- **Vector Database Stats**: Total vectors, model info, index status
- **Performance Metrics**: Error rates, uptime, request counts
- **Quick Statistics**: Searchable cases, index size, training status

### 2. 🏥 **Health Monitor** (`/health`)
- **System Resources**: CPU, Memory, Disk usage with progress bars
- **Index Health**: FAISS index and metadata status
- **Performance Metrics**: Response times, error rates, uptime
- **Active Alerts**: Real-time alerts with severity levels
- **Data Freshness**: Index age and update recommendations

### 3. ⚡ **Performance Analytics** (`/performance`)
- **Performance Overview**: Total operations, error rates, response times
- **Operation Statistics**: Detailed metrics per operation type
- **Interactive Charts**: Bar charts showing operation performance
- **Batch Processing**: Throughput analysis for large-scale operations
- **Optimization Recommendations**: AI-driven performance suggestions

### 4. 💾 **Backup Manager** (`/backup`)
- **Backup Statistics**: Total backups, sizes, latest backup info
- **Create Backups**: Manual backup creation with descriptions
- **Backup History**: Table view of all available backups
- **Restore Operations**: Safe restore with automatic pre-restore backups
- **Delete Management**: Remove old or unnecessary backups

### 5. 🔍 **Search Test Interface** (`/search`)
- **Interactive Search**: Test vector similarity search
- **Adjustable Parameters**: Top-K results, similarity thresholds
- **Real-time Results**: Live search with similarity scores
- **Search History**: Track previous searches and performance
- **Sample Queries**: Pre-built test queries for quick testing
- **Result Analysis**: Detailed similarity scoring and case previews

### 6. 🧹 **Data Quality Dashboard** (`/quality`)
- **Quality Overview**: Total records, processed, filtered, duplicates
- **Quality Distribution**: Pie chart of data quality categories
- **Filter Performance**: Bar chart showing quality filter effectiveness
- **Field Completeness**: Analysis of data completeness by field
- **Quality Actions**: Tools for data cleanup and reprocessing

## 🔧 Technical Architecture

### Frontend Stack
- **React 18**: Modern React with hooks and functional components
- **Material-UI 5**: Google's Material Design components
- **Vite**: Fast build tool with hot module replacement
- **Recharts**: Interactive data visualization charts
- **Axios**: HTTP client with API proxy configuration

### API Integration
- **Proxy Configuration**: Vite proxies `/api/*` to `localhost:8008`
- **Real-time Updates**: Automatic refresh intervals (30-60 seconds)
- **Error Handling**: Graceful error displays with retry options
- **Mock Data**: Fallback data for features under development

### Key Components

```javascript
// Main application structure
src/
├── components/
│   └── Sidebar.jsx          # Navigation sidebar
├── pages/
│   ├── Dashboard.jsx        # Main dashboard
│   ├── HealthMonitor.jsx    # Health monitoring
│   ├── Performance.jsx      # Performance analytics
│   ├── BackupManager.jsx    # Backup management
│   ├── SearchTest.jsx       # Search testing
│   └── DataQuality.jsx      # Data quality metrics
├── services/
│   └── api.js              # API client and endpoints
└── App.jsx                 # Main app with routing
```

## 🎯 Usage Scenarios

### 1. **System Monitoring**
1. Open Dashboard to view overall system health
2. Check Health Monitor for detailed resource usage
3. Review Performance Analytics for optimization opportunities
4. Set up alerts for critical thresholds

### 2. **Search Testing**
1. Navigate to Search Test Interface
2. Enter test queries or use sample queries
3. Adjust similarity thresholds to find optimal settings
4. Review search history for performance trends

### 3. **Backup Management**
1. Go to Backup Manager
2. Create manual backups before major changes
3. Monitor backup storage usage
4. Restore previous versions if needed

### 4. **Performance Optimization**
1. Check Performance Analytics for slow operations
2. Review optimization recommendations
3. Monitor batch processing throughput
4. Track improvements over time

### 5. **Data Quality Assurance**
1. Review Data Quality Dashboard metrics
2. Check field completeness percentages
3. Monitor duplicate detection effectiveness
4. Run data cleanup operations as needed

## 🔒 Security & Access

- **Internal Use Only**: No authentication required (admin tool)
- **Network Access**: Runs on localhost by default
- **API Proxy**: Secure proxy to backend API
- **CORS Enabled**: For development flexibility

## 🛠️ Development & Customization

### Adding New Features

1. **Create New Page Component**:
   ```javascript
   // src/pages/NewFeature.jsx
   import React from 'react'
   import { Card, CardContent, Typography } from '@mui/material'
   
   function NewFeature() {
     return (
       <Card>
         <CardContent>
           <Typography variant="h4">New Feature</Typography>
         </CardContent>
       </Card>
     )
   }
   
   export default NewFeature
   ```

2. **Add Route to App.jsx**:
   ```javascript
   import NewFeature from './pages/NewFeature'
   
   // Add to Routes
   <Route path="/newfeature" element={<NewFeature />} />
   ```

3. **Add to Sidebar Navigation**:
   ```javascript
   const menuItems = [
     // ... existing items
     { text: 'New Feature', icon: <Icon />, path: '/newfeature' },
   ]
   ```

### API Integration

```javascript
// Add new API endpoints in src/services/api.js
export const newFeatureAPI = {
  getData: () => api.get('/new-feature/data'),
  updateSettings: (settings) => api.post('/new-feature/settings', settings),
}
```

### Styling and Themes

```javascript
// Customize theme in src/main.jsx
const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
  },
})
```

## 📊 API Endpoints Used

The Admin UI integrates with these backend endpoints:

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/detailed` - Comprehensive health data
- `GET /health/metrics` - Metrics summary
- `GET /health/report?hours=24` - Time-based health report

### Performance
- `GET /performance/report` - Performance overview
- `GET /performance/operations` - Operation statistics
- `GET /performance/batch` - Batch processing metrics
- `GET /performance/recommendations` - Optimization suggestions
- `POST /performance/save` - Save metrics to disk

### Vector Database
- `GET /stats` - Database statistics
- `POST /search` - Vector similarity search
- `GET /search?q=query` - GET-based search

### Backup (Mock Data)
- Backup endpoints are mocked in frontend
- Ready for backend implementation

## 🎨 UI Design Principles

### Material Design
- Consistent spacing and typography
- Color-coded status indicators (green=good, yellow=warning, red=error)
- Responsive grid layout for all screen sizes
- Intuitive navigation with clear icons

### Data Visualization
- Interactive charts with hover tooltips
- Consistent color schemes across charts
- Progressive disclosure (overview → details)
- Real-time data updates

### User Experience
- Loading states for all async operations
- Error boundaries with retry options
- Keyboard shortcuts and accessibility
- Mobile-responsive design

## 🚀 Production Deployment

### Build for Production
```bash
cd admin-ui
npm run build
npm run preview  # Test production build
```

### Nginx Configuration
```nginx
server {
    listen 4001;
    root /path/to/admin-ui/dist;
    index index.html;
    
    location /api/ {
        proxy_pass http://localhost:8008/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### Environment Variables
```bash
# .env.production
VITE_API_BASE_URL=https://your-api-server.com
VITE_REFRESH_INTERVAL=60000
```

## 📞 Support & Troubleshooting

### Common Issues

1. **"Connection Failed" Error**
   - Ensure API server is running on port 8008
   - Check browser network tab for CORS issues
   - Verify proxy configuration in vite.config.js

2. **Charts Not Loading**
   - Install Recharts: `npm install recharts`
   - Check browser console for errors
   - Verify data format matches chart expectations

3. **Slow Performance**
   - Increase refresh intervals in components
   - Optimize data fetching with React.memo
   - Consider pagination for large datasets

4. **Mobile Display Issues**
   - Test responsive breakpoints
   - Check Material-UI Grid system usage
   - Verify viewport meta tag in index.html

### Getting Help
- Check browser developer console for errors
- Review API server logs for backend issues
- Use React DevTools for component debugging
- Monitor network requests in DevTools

---

## 🎉 Congratulations!

You now have a fully functional React Admin UI for the KMS-SFDC Vector Database system, featuring:

✅ **Real-time monitoring and health checks**  
✅ **Interactive performance analytics**  
✅ **Comprehensive backup management**  
✅ **Advanced search testing capabilities**  
✅ **Data quality monitoring and visualization**  
✅ **Professional Material-UI design**  
✅ **Responsive and accessible interface**  

**Access your Admin UI at: http://localhost:4001**