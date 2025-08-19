# KMS-SFDC Vector Database

A comprehensive FAISS-based vector database system for HPE Salesforce case data similarity search, featuring automated data synchronization, performance monitoring, and web-based administration.

## Overview

This project builds and maintains a vector database from HPE SFDC case data to enable semantic similarity search for case issues and resolutions. The system uses Facebook AI Similarity Search (FAISS) for efficient vector operations, includes automated data synchronization, comprehensive testing, and provides both REST API and web-based administration interfaces.

## 🚀 Key Features

### Core Functionality
- **SFDC Data Extraction**: Automated batch extraction with incremental updates and **attachment content extraction** (PDF, DOCX, TXT)
- **Text Processing**: Advanced preprocessing with configurable field selection and **attachment text integration**
- **Extracted Attachment Data**: The text extracted by the text extractor is stored in the description_summary column       within the metadata
- **Local Vector Embedding**: Nomic embed-text-v1.5 running entirely locally (no API calls)
- **FAISS Integration**: High-performance similarity search with multiple index types
- **REST API**: Comprehensive FastAPI-based service with full OpenAPI documentation

### Automation & Scheduling  
- **Automated Scheduler**: Configurable interval/daily/cron-based data synchronization
- **Incremental Updates**: Smart sync with backup/restore capabilities  
- **Manual Sync**: On-demand synchronization with progress monitoring
- **Error Recovery**: Automatic rollback on sync failures with detailed logging

### Administration & Monitoring
- **Web Admin Dashboard**: React-based UI for complete system management
- **Real-time Monitoring**: Performance metrics, health checks, and status tracking
- **Scheduler Management**: Configure sync intervals, enable/disable jobs, view history
- **Performance Analytics**: Detailed timing metrics and optimization recommendations

### Testing & Quality Assurance
- **Comprehensive Test Suite**: Unit, integration, and performance tests
- **Load Testing Ready**: Framework for testing at scale (3000+ tickets/day)
- **Backup Management**: Automated backups with restoration capabilities
- **Health Monitoring**: Continuous system health validation

### Enterprise Ready
- **Fully Local**: No external API dependencies for core operations
- **Security Focused**: Secure credential management and validation
- **Scalable Architecture**: Designed for high-volume production use
- **Docker Support**: Containerized deployment with development containers

## Quick Start

### 1. Environment Setup

```bash
# Clone and setup
git clone <repository-url>
cd KMS-SFDC

# UV will be automatically installed if not present
make setup-env

# Configure Salesforce credentials
cp .env.example .env
# Edit .env with your SFDC credentials

# Install attachment processing dependencies
pip install pypdf python-docx
```

### 2. Install Dependencies (UV automatically handles this)

Dependencies are automatically installed with UV during setup. For manual installation:

```bash
# Install with UV (recommended - much faster than pip)
make install

# Or fallback to pip if needed
make install-pip
```

### 3. Test Local Embeddings

```bash
make test-embeddings
```

### 4. Build Initial Index

```bash
# Build from all available data (last 2 years) with attachments
make build-index

# Or build from sample data for testing
make build-index-sample
```

**Note**: The system now automatically extracts and indexes content from Salesforce attachments (PDF, DOCX, TXT) and integrates it with case metadata for enhanced search capabilities.
```

### 5. Start Services

```bash
# Start API server (includes scheduler)
make run-api

# Start admin UI (in separate terminal)
cd admin-ui && npm run dev
```

Services will be available at:
- **API**: `http://localhost:8008` (with OpenAPI docs at `/docs`)
- **Admin UI**: `http://localhost:4001`

## Project Structure

```
KMS-SFDC/
├── src/
│   ├── data_extraction/    # Salesforce data extraction and client
│   ├── vectorization/      # FAISS vector database operations
│   ├── search/            # FastAPI REST API service
│   ├── scheduler/         # Automated sync job scheduling
│   ├── load_testing/      # Load testing framework (planned)
│   └── utils/             # Configuration, text processing, monitoring
├── admin-ui/             # React-based admin dashboard
│   ├── src/components/   # UI components for management
│   └── public/          # Static assets
├── tests/               # Comprehensive test suite
│   ├── unit/           # Unit tests for all components
│   ├── integration/    # Integration tests
│   └── performance/    # Performance and load tests  
├── config/             # Configuration files and templates
├── scripts/            # Utility and deployment scripts
├── data/               # Generated indexes, metadata, backups
├── docs/               # Comprehensive documentation
└── logs/               # Application and scheduler logs
```

## Configuration

Key configuration is managed in `config/config.yaml`:

- **Salesforce**: Connection settings and query parameters
- **Vector Database**: Nomic model selection, FAISS index type, storage paths
- **Text Processing**: Preprocessing options and field selection
- **API Settings**: Server configuration and search parameters

The system uses **Nomic embed-text-v1.5** model which runs entirely locally without requiring API keys or internet connectivity for embeddings.

## API Usage

### Search for Similar Cases

```bash
# POST request
curl -X POST "http://localhost:8008/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "user login issues", "top_k": 10}'

# GET request  
curl "http://localhost:8008/search?q=password%20reset&top_k=5&threshold=0.7"
```

### System Health & Status

```bash
# Basic health check
curl "http://localhost:8008/health"

# Detailed health with metrics
curl "http://localhost:8008/health/detailed"

# Sync status and statistics
curl "http://localhost:8008/sync/status"
```

### Scheduler Management

```bash
# Get all scheduled jobs
curl "http://localhost:8008/scheduler/jobs"

# Update job schedule
curl -X PUT "http://localhost:8008/scheduler/jobs/sfdc_sync" \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "schedule": {"type": "interval", "interval_minutes": 60}}'

# Trigger manual sync
curl -X POST "http://localhost:8008/sync/manual"
```

### Performance Metrics

```bash
# Performance report
curl "http://localhost:8008/performance/report"

# Operation statistics
curl "http://localhost:8008/performance/operations"
```

## Development

### Running Tests

```bash
make test          # All tests with coverage
make test-unit     # Unit tests only  
make test-integration  # Integration tests
make test-performance  # Performance tests
make lint          # Code quality checks
make format        # Code formatting
```

### Development Mode

```bash
make run-api-dev   # API with auto-reload
cd admin-ui && npm run dev  # Admin UI with hot reload
```

### Load Testing

```bash
# Install load testing dependencies
uv pip install locust

# Run load tests (example for 3000 tickets/day)
locust -f tests/load_testing/locustfile.py --host=http://localhost:8008
```

## 🛠️ Administration

### Web Admin Dashboard

Access the admin dashboard at `http://localhost:4001` for:

- **System Overview**: Health status, performance metrics, database statistics
- **Scheduler Management**: Configure sync intervals, enable/disable jobs, view history
- **Manual Operations**: Trigger syncs, view progress, manage backups
- **Performance Monitoring**: Real-time metrics, optimization recommendations

### Scheduler Configuration

The automated scheduler supports:

- **Interval-based**: Every N minutes/hours (e.g., every 60 minutes)
- **Daily scheduling**: Specific time of day (e.g., 2:00 AM)
- **Cron expressions**: Advanced scheduling patterns
- **Manual triggers**: On-demand synchronization

### Backup Management

Automatic backups are created before each sync operation:

```bash
# List available backups
curl "http://localhost:8008/backup/list"

# Restore from backup
curl -X POST "http://localhost:8008/backup/restore/backup_id"
```

## 🚀 Deployment Considerations

### Security
- Store SFDC credentials securely (environment variables)
- Implement API authentication for production use
- Configure CORS appropriately for your environment
- Enable HTTPS for production deployments
- Secure admin UI access with authentication

### Performance  
- Adjust batch sizes based on available memory (default: 2000 cases)
- Consider using HNSW index for large datasets (>100k cases)
- Monitor API response times and scale horizontally if needed
- Use caching for frequently accessed status endpoints
- Optimize sync schedules based on SFDC API limits

### Monitoring
- Built-in performance metrics and health monitoring
- Enable metrics endpoint for Prometheus integration
- Set up log aggregation for centralized monitoring
- Configure alerts for sync failures and performance degradation
- Monitor disk space for vector indexes and backups

### High Availability
- Implement database replication for vector indexes
- Use load balancers for API endpoints
- Configure automatic restart for scheduler services
- Set up monitoring for service health and recovery

## Integration with Cognate AI

The vector database is designed to replace or supplement existing lexical search (API2: Coveo) in the KM Generation Agent:

1. **API Compatibility**: REST endpoints match expected integration patterns
2. **Response Format**: Structured JSON responses with similarity scores
3. **Fallback Support**: Can be used alongside existing search methods

## Troubleshooting

### Common Issues

- **SFDC Connection Fails**: Verify credentials and security token in `.env`
- **Nomic Model Loading Error**: Run `make setup-nomic` to ensure local setup
- **Out of Memory**: Reduce batch size in configuration  
- **Index Build Slow**: Check network connectivity to SFDC and consider incremental builds
- **Search Returns Empty**: Verify index exists and similarity threshold is not too high
- **Embedding Test Fails**: Ensure Nomic is properly installed with `pip install nomic`

### Logs

Check application logs in the `logs/` directory for detailed error information.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review application logs for error details  
3. Consult project documentation in `docs/` directory
4. Contact the development team with specific error messages