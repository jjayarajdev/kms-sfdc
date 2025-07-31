# KMS-SFDC Documentation

This directory contains comprehensive documentation for the KMS-SFDC Vector Database system.

## 📚 Documentation Index

### Getting Started
- **[Main README](../README.md)** - Project overview, quick start, and basic usage
- **[SFDC Connection Guide](SFDC_CONNECTION_GUIDE.md)** - Setting up Salesforce connectivity
- **[UV Migration Guide](UV_MIGRATION.md)** - Python package management with UV

### API & Development
- **[API Documentation](API_DOCUMENTATION.md)** - Complete REST API reference
- **[Testing Guide](TESTING_GUIDE.md)** - Unit, integration, and performance testing
- **[Load Testing Guide](LOAD_TESTING_GUIDE.md)** - Load testing with Locust for 3000+ tickets/day

### Administration & Operations
- **[Admin UI Guide](ADMIN_UI_GUIDE.md)** - Web-based administration interface
- **[Scheduler Guide](SCHEDULER_GUIDE.md)** - Automated data synchronization
- **[Scheduler Fixes](SCHEDULER_FIXES.md)** - Performance fixes and optimizations
- **[Deployment Guide](DEPLOYMENT_GUIDE.md)** - Production deployment procedures

### Architecture & Design
- **[System Enhancements](ENHANCEMENTS.md)** - Current system improvements
- **[Scale Architecture](SCALE_ARCHITECTURE.md)** - Scalability considerations
- **[Technical Architecture Diagrams](technical-architecture.svg)** - System architecture overview

## 🏗️ System Architecture

The KMS-SFDC system consists of several key components:

### Core Components
- **SFDC Data Extraction**: Automated Salesforce case data extraction
- **Vector Database**: FAISS-based similarity search with Nomic embeddings
- **REST API**: FastAPI-based service with comprehensive endpoints
- **Scheduler Service**: Automated data synchronization with configurable intervals
- **Admin UI**: React-based web interface for system management

### Supporting Systems
- **Health Monitoring**: Real-time system health and performance tracking
- **Backup Management**: Automated backup and restore capabilities
- **Performance Analytics**: Detailed metrics and optimization recommendations
- **Load Testing**: Comprehensive testing framework for high-volume scenarios

## 🚀 Quick Navigation

### For Developers
1. Start with the [Main README](../README.md) for project setup
2. Review [API Documentation](API_DOCUMENTATION.md) for endpoint details
3. Follow [Testing Guide](TESTING_GUIDE.md) for development testing

### For System Administrators
1. Review [Deployment Guide](DEPLOYMENT_GUIDE.md) for production setup
2. Configure using [Admin UI Guide](ADMIN_UI_GUIDE.md)
3. Set up monitoring per [Scheduler Guide](SCHEDULER_GUIDE.md)

### For Operations Teams
1. Monitor system health via [Admin UI Guide](ADMIN_UI_GUIDE.md)
2. Handle incidents using [API Documentation](API_DOCUMENTATION.md)
3. Scale system following [Scale Architecture](SCALE_ARCHITECTURE.md)

### For Performance Testing
1. Review [Load Testing Guide](LOAD_TESTING_GUIDE.md) for comprehensive testing
2. Set up Locust framework for 3000+ tickets/day scenarios
3. Monitor performance using built-in analytics

## 🔧 Configuration Reference

### Environment Variables
```bash
# Core Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO

# Salesforce Configuration
SFDC_USERNAME=your-username
SFDC_PASSWORD=your-password
SFDC_SECURITY_TOKEN=your-token
SFDC_LOGIN_URL=https://login.salesforce.com

# API Configuration
API_HOST=0.0.0.0
API_PORT=8008

# Vector Database Configuration
VECTOR_MODEL=nomic-embed-text-v1.5
INDEX_TYPE=IndexFlatIP
INDEX_PATH=data/faiss_index.bin
```

### Key Configuration Files
- `config/config.yaml` - Main system configuration
- `data/scheduler_config.json` - Scheduler job configuration
- `admin-ui/.env` - Admin UI environment settings
- `.env` - Application environment variables

## 📊 Monitoring & Observability

### Health Endpoints
- `GET /health` - Basic health check
- `GET /health/detailed` - Comprehensive system health
- `GET /sync/status` - Data synchronization status
- `GET /performance/report` - Performance metrics

### Key Metrics
- **Search Performance**: Response times, throughput
- **Data Sync**: Success rates, processing times
- **System Resources**: CPU, memory, disk usage
- **API Usage**: Request rates, error rates

## 🔒 Security Considerations

### Authentication
- API key authentication for production
- JWT tokens for admin operations
- Rate limiting on all endpoints

### Data Security
- Encrypted Salesforce credentials
- Secure vector database storage
- Audit logging for all operations

### Network Security
- HTTPS/TLS encryption
- Firewall configuration
- VPN access for admin interfaces

## 🚨 Troubleshooting

### Common Issues
1. **SFDC Connection Failures**: Check credentials and network connectivity
2. **Vector DB Not Ready**: Verify index files and model availability
3. **High Memory Usage**: Review batch sizes and dataset size
4. **Slow Search Performance**: Check index optimization and system resources

### Support Resources
- Application logs in `logs/` directory
- Health check endpoints for system status
- Performance metrics for optimization
- Backup and recovery procedures

## 📈 Performance Benchmarks

### Target Performance Metrics
| Operation | Target | Acceptable | Maximum |
|-----------|--------|------------|---------|
| Search Query | < 50ms | < 100ms | < 200ms |
| Health Check | < 10ms | < 25ms | < 50ms |
| Data Sync | < 5min/10k cases | < 10min/10k cases | < 20min/10k cases |

### Load Testing Targets
- **Steady State**: 3000 tickets/day (2.08/minute)
- **Peak Load**: 10x normal load for 2 hours
- **Soak Testing**: 72+ hours continuous operation

## 🔄 Update Procedures

### Regular Updates
1. Review [Scheduler Fixes](SCHEDULER_FIXES.md) for recent improvements
2. Update system following [Deployment Guide](DEPLOYMENT_GUIDE.md)
3. Run comprehensive tests per [Testing Guide](TESTING_GUIDE.md)
4. Monitor system performance post-update

### Emergency Updates
1. Follow rollback procedures in [Deployment Guide](DEPLOYMENT_GUIDE.md)
2. Use backup/restore from [Admin UI Guide](ADMIN_UI_GUIDE.md)
3. Contact support with system logs and error details

## 📞 Support & Contact

For additional support:
1. Review relevant documentation sections above
2. Check application logs for detailed error information
3. Use admin UI for system status and diagnostics
4. Contact development team with specific error messages and logs

---

*This documentation is maintained alongside the KMS-SFDC system and updated with each release.*