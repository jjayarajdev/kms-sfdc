# Testing Guide

Comprehensive testing documentation for the KMS-SFDC Vector Database system.

## Testing Overview

The KMS-SFDC system includes comprehensive testing across multiple layers:

- **Unit Tests**: Individual component testing
- **Integration Tests**: Cross-component workflow testing  
- **Performance Tests**: Load and performance validation
- **Load Testing**: High-volume simulation with Locust
- **End-to-End Tests**: Complete workflow validation

## Test Structure

```
tests/
├── unit/
│   ├── test_vector_db.py        # Vector database operations
│   ├── test_sfdc_client.py      # SFDC data extraction
│   ├── test_text_processor.py   # Text preprocessing
│   ├── test_api.py             # API endpoints
│   ├── test_config.py          # Configuration management
│   ├── test_health_monitor.py  # Health monitoring
│   └── test_backup_manager.py  # Backup operations
├── integration/
│   ├── test_search_workflow.py  # End-to-end search
│   ├── test_sfdc_integration.py # SFDC data flow
│   └── test_api_integration.py  # API integration
├── performance/
│   ├── test_large_dataset.py    # Large data handling
│   ├── test_concurrent_search.py # Concurrent operations
│   └── test_memory_usage.py     # Memory profiling
└── load_testing/
    ├── locustfile.py            # Locust load tests
    ├── steady_state_test.py     # 3000 tickets/day simulation
    └── peak_load_test.py        # Burst load testing
```

## Running Tests

### All Tests with Coverage

```bash
make test
```

This runs the complete test suite with coverage reporting.

### Unit Tests Only

```bash
make test-unit

# Or directly with pytest
pytest tests/unit/ -v
```

### Integration Tests

```bash
make test-integration

# Or directly with pytest
pytest tests/integration/ -v
```

### Performance Tests

```bash
make test-performance

# Or directly with pytest
pytest tests/performance/ -v -s
```

### Specific Test Files

```bash
# Run specific test file
pytest tests/unit/test_vector_db.py -v

# Run specific test method
pytest tests/unit/test_vector_db.py::TestVectorDatabase::test_search_functionality -v

# Run tests with specific markers
pytest -m "not slow" -v
```

## Test Configuration

### Environment Setup

Tests use a separate configuration to avoid affecting production data:

```bash
# Test environment variables
export TESTING=true
export TEST_DATA_DIR="tests/data"
export TEST_INDEX_PATH="tests/data/test_index.faiss"
```

### Test Data

Test fixtures provide realistic but controlled data:

```python
@pytest.fixture
def sample_case_data():
    """Create sample case data for testing."""
    return pd.DataFrame([
        {
            'Id': 'case_001',
            'Case_Number': 'CASE-001',
            'Subject_Description': 'Server crashes unexpectedly',
            'Description_Description': 'Production server experiencing random crashes',
            'Issue_Plain_Text': 'System instability causing downtime',
            'Cause_Plain_Text': 'Memory leak in application process',
            'Resolution_Plain_Text': 'Updated application to version 2.1.3',
            'Status_Text': 'Closed',
            'TextBody': 'Full case description with technical details...',
            'CreatedDate': '2024-01-15T10:30:00Z'
        }
    ])
```

## Unit Testing

### Vector Database Tests

Tests cover all vector database operations:

```python
class TestVectorDatabase:
    def test_build_index(self, sample_case_data):
        """Test index building with sample data."""
        
    def test_search_functionality(self, trained_vector_db):
        """Test similarity search operations."""
        
    def test_incremental_updates(self, trained_vector_db, new_case_data):
        """Test adding new cases to existing index."""
        
    def test_save_and_load_index(self, trained_vector_db):
        """Test persistence operations."""
```

### SFDC Client Tests

Mock SFDC responses for reliable testing:

```python
class TestSFDCClient:
    @patch('simple_salesforce.Salesforce')
    def test_connection(self, mock_sf):
        """Test SFDC connection establishment."""
        
    @patch('simple_salesforce.Salesforce')
    def test_data_extraction(self, mock_sf):
        """Test case data extraction."""
        
    def test_batch_processing(self, mock_sfdc_client):
        """Test batched data extraction."""
```

### API Tests

Test all API endpoints with FastAPI test client:

```python
class TestSearchAPI:
    def test_search_endpoint(self, client, trained_vector_db):
        """Test POST /search endpoint."""
        response = client.post("/search", json={
            "query": "server issues",
            "top_k": 5
        })
        assert response.status_code == 200
        
    def test_health_endpoint(self, client):
        """Test GET /health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
```

## Integration Testing

### Search Workflow Tests

Test complete search workflows:

```python
class TestSearchWorkflow:
    def test_end_to_end_search(self, sfdc_client, text_processor, vector_db):
        """Test complete search workflow from data extraction to results."""
        
    def test_incremental_sync_workflow(self):
        """Test incremental data synchronization."""
        
    def test_backup_restore_workflow(self):
        """Test backup creation and restoration."""
```

### SFDC Integration Tests

Test real SFDC integration (requires valid credentials):

```python
class TestSFDCIntegration:
    @pytest.mark.skipif(not os.getenv("SFDC_INTEGRATION_TEST"), 
                       reason="SFDC integration tests disabled")
    def test_real_sfdc_connection(self):
        """Test connection to real SFDC instance."""
        
    def test_data_extraction_workflow(self):
        """Test complete data extraction workflow."""
```

### API Integration Tests

Test API interactions with real services:

```python
class TestAPIIntegration:
    def test_scheduler_integration(self, api_client):
        """Test scheduler API integration."""
        
    def test_sync_status_integration(self, api_client):
        """Test sync status reporting."""
```

## Performance Testing

### Large Dataset Tests

Test system behavior with large datasets:

```python
class TestLargeDataset:
    @pytest.mark.slow
    def test_large_index_build(self, large_case_dataset):
        """Test building index with 50k+ cases."""
        
    @pytest.mark.slow  
    def test_memory_usage_large_dataset(self, large_case_dataset):
        """Monitor memory usage with large datasets."""
```

### Concurrent Operations

Test system under concurrent load:

```python
class TestConcurrentSearch:
    def test_concurrent_searches(self, trained_vector_db):
        """Test multiple concurrent search operations."""
        import threading
        
        def search_worker():
            results = vector_db.search("test query")
            assert len(results) > 0
            
        threads = [threading.Thread(target=search_worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
```

## Load Testing with Locust

### Installation

```bash
uv pip install locust
```

### Basic Load Test

```python
# tests/load_testing/locustfile.py
from locust import HttpUser, task, between

class SFDCLoadTestUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(5)
    def search_cases(self):
        """Simulate case searches - most frequent operation."""
        self.client.post("/search", json={
            "query": "server performance issues",
            "top_k": 10
        })
    
    @task(1)
    def check_health(self):
        """Simulate health checks."""
        self.client.get("/health")
        
    @task(1)
    def get_sync_status(self):
        """Simulate status checks."""
        self.client.get("/sync/status")
```

### Running Load Tests

```bash
# Basic load test
locust -f tests/load_testing/locustfile.py --host=http://localhost:8008

# Headless mode with specific parameters
locust -f tests/load_testing/locustfile.py \
  --host=http://localhost:8008 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=300s \
  --headless

# 3000 tickets/day simulation (steady state)
locust -f tests/load_testing/steady_state_test.py \
  --host=http://localhost:8008 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=24h

# Peak load testing
locust -f tests/load_testing/peak_load_test.py \
  --host=http://localhost:8008 \
  --users=200 \
  --spawn-rate=10 \
  --run-time=2h
```

### Load Test Scenarios

**Steady State (3000 tickets/day):**
- 50 concurrent users
- ~2.08 tickets/minute creation rate
- Search:creation ratio of 5:1
- Run for 24 hours

**Peak Load (10x normal):**
- 200 concurrent users  
- ~20 tickets/minute creation rate
- Higher search frequency
- Run for 2 hours

**Soak Testing:**
- Moderate load (25 users)
- Run for 72+ hours
- Monitor memory leaks and resource accumulation

## Test Markers

Use pytest markers to categorize tests:

```python
# Slow tests (>30 seconds)
@pytest.mark.slow

# Tests requiring SFDC connection
@pytest.mark.sfdc_integration

# Performance tests
@pytest.mark.performance

# Load tests
@pytest.mark.load_test
```

Run specific test categories:

```bash
# Skip slow tests
pytest -m "not slow"

# Run only performance tests
pytest -m performance

# Run integration tests only
pytest -m sfdc_integration
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt
          uv pip install -r requirements-test.txt
      
      - name: Run tests
        run: |
          pytest tests/unit/ tests/integration/ --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v1
```

## Performance Benchmarks

### Target Performance Metrics

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Single search query | < 50ms | < 100ms |
| Batch search (10 queries) | < 200ms | < 500ms |
| Index build (10k cases) | < 5 min | < 10 min |
| Incremental update (100 cases) | < 30s | < 60s |

### Memory Usage Targets

| Dataset Size | RAM Usage | Index Size |
|-------------|-----------|------------|
| 10k cases | < 500MB | < 100MB |
| 50k cases | < 2GB | < 400MB |
| 100k cases | < 4GB | < 800MB |

## Troubleshooting Tests

### Common Issues

**Test Database Conflicts:**
```bash
# Clean test data
rm -rf tests/data/*
pytest tests/unit/test_vector_db.py
```

**SFDC Connection in Tests:**
```bash
# Skip SFDC integration tests
export SFDC_INTEGRATION_TEST=false
pytest tests/
```

**Memory Issues in Performance Tests:**
```bash
# Run performance tests individually
pytest tests/performance/test_large_dataset.py::test_build_large_index -v -s
```

**Locust Load Test Issues:**
```bash
# Check API is running
curl http://localhost:8008/health

# Start with fewer users
locust -f tests/load_testing/locustfile.py --host=http://localhost:8008 --users=5
```

### Test Debugging

Enable verbose logging in tests:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or use pytest with log output
pytest tests/ -v -s --log-cli-level=DEBUG
```

## Test Data Management

### Sample Data Generation

```python
def generate_test_cases(count=1000):
    """Generate realistic test case data."""
    cases = []
    for i in range(count):
        cases.append({
            'Id': f'case_{i:06d}',
            'Case_Number': f'CASE-{i:06d}',
            'Subject_Description': fake.sentence(),
            'Description_Description': fake.text(),
            # ... more fields
        })
    return pd.DataFrame(cases)
```

### Test Database Cleanup

```python
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Clean up test data after each test."""
    yield
    
    # Cleanup test files
    test_files = ['tests/data/test_index.faiss', 'tests/data/test_metadata.json']
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
```

This comprehensive testing guide ensures the KMS-SFDC system is thoroughly validated across all scenarios from unit testing to high-volume load testing.