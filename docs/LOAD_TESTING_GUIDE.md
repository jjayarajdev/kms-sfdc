# Load Testing Guide

Comprehensive guide for load testing the KMS-SFDC Vector Database system at scale, including 3000+ tickets per day scenarios.

## Overview

This guide covers load testing strategies for validating the KMS-SFDC system's performance under various load conditions, with specific focus on handling 3000 tickets per day and burst scenarios.

## Load Testing Framework: Locust

We use [Locust](https://locust.io/) as our primary load testing framework due to its Python integration and flexibility for testing our FastAPI endpoints.

### Why Locust?

- **Python Integration**: Seamless integration with our existing Python codebase
- **HTTP/REST API Testing**: Perfect for testing our FastAPI endpoints
- **Realistic User Simulation**: Can simulate complex user behavior patterns  
- **Distributed Testing**: Scale across multiple machines if needed
- **Real-time Monitoring**: Built-in web UI for live test monitoring
- **Flexible Scenarios**: Easy to define various load patterns

## Installation

```bash
# Install Locust
uv pip install locust

# Verify installation
locust --version
```

## Load Testing Scenarios

### Scenario 1: Steady State Load (3000 tickets/day)

**Target**: 3000 tickets/day = ~2.08 tickets/minute = ~35 seconds between tickets

```python
# tests/load_testing/steady_state_test.py
from locust import HttpUser, task, between
import random
import json

class SteadyStateUser(HttpUser):
    wait_time = between(30, 40)  # ~35 seconds between actions
    
    def on_start(self):
        """Initialize user session."""
        self.search_queries = [
            "server performance issues",
            "user login problems", 
            "network connectivity failure",
            "application crashes",
            "database connection timeout",
            "SSL certificate errors",
            "memory leak investigation",
            "disk space warnings"
        ]
    
    @task(1)
    def create_ticket_simulation(self):
        """Simulate ticket creation (triggers sync)."""
        # This simulates the effect of a new ticket being processed
        response = self.client.post("/sync/manual")
        
    @task(8)  
    def search_similar_cases(self):
        """Simulate users searching for similar cases."""
        query = random.choice(self.search_queries)
        response = self.client.post("/search", json={
            "query": query,
            "top_k": random.randint(5, 15),
            "similarity_threshold": random.uniform(0.6, 0.8)
        })
        
    @task(2)
    def check_system_status(self):
        """Simulate admin users checking system status."""
        endpoints = ["/health", "/sync/status", "/stats"]
        endpoint = random.choice(endpoints)
        response = self.client.get(endpoint)
```

**Running Steady State Test:**
```bash
locust -f tests/load_testing/steady_state_test.py \
  --host=http://localhost:8008 \
  --users=50 \
  --spawn-rate=5 \
  --run-time=24h \
  --headless \
  --html=reports/steady_state_report.html
```

### Scenario 2: Peak Load Testing (Burst Scenarios)

**Target**: 10x normal load during incident response or busy periods

```python  
# tests/load_testing/peak_load_test.py
from locust import HttpUser, task, between
import random

class PeakLoadUser(HttpUser):
    wait_time = between(3, 8)  # Much faster during peak times
    
    def on_start(self):
        """Initialize for high-intensity testing."""
        self.incident_queries = [
            "critical system outage",
            "production server down", 
            "network outage affecting users",
            "database corruption emergency",
            "security breach investigation",
            "application not responding"
        ]
        
    @task(3)
    def urgent_ticket_search(self):
        """Simulate urgent case searches during incidents."""
        query = random.choice(self.incident_queries)
        response = self.client.post("/search", json={
            "query": query,
            "top_k": 20,
            "similarity_threshold": 0.5
        })
        
    @task(2)
    def rapid_status_checks(self):
        """Frequent status checking during incidents."""
        response = self.client.get("/health/detailed")
        
    @task(1)
    def manual_sync_trigger(self):
        """Manual syncs triggered during busy periods."""
        response = self.client.post("/sync/manual")
        
    @task(1)
    def scheduler_management(self):
        """Admin operations during peak times."""
        response = self.client.get("/scheduler/jobs")
```

**Running Peak Load Test:**
```bash
locust -f tests/load_testing/peak_load_test.py \
  --host=http://localhost:8008 \
  --users=200 \
  --spawn-rate=20 \
  --run-time=2h \
  --headless \
  --html=reports/peak_load_report.html
```

### Scenario 3: Soak Testing (Long-term Stability)

**Target**: Extended testing to identify memory leaks and resource accumulation

```python
# tests/load_testing/soak_test.py
from locust import HttpUser, task, between
import random

class SoakTestUser(HttpUser):
    wait_time = between(60, 120)  # Slower but sustained load
    
    @task(10)
    def sustained_search_load(self):
        """Sustained search operations."""
        queries = [
            "performance degradation",
            "system monitoring alerts", 
            "user access issues",
            "application errors"
        ]
        query = random.choice(queries)
        response = self.client.post("/search", json={
            "query": query,
            "top_k": 10
        })
        
    @task(1)
    def periodic_health_check(self):
        """Regular health monitoring."""
        response = self.client.get("/health/detailed")
        
    @task(1)
    def memory_intensive_operation(self):
        """Operations that may accumulate memory."""
        response = self.client.get("/performance/report")
```

**Running Soak Test:**
```bash
locust -f tests/load_testing/soak_test.py \
  --host=http://localhost:8008 \
  --users=25 \
  --spawn-rate=2 \
  --run-time=72h \
  --headless \
  --html=reports/soak_test_report.html
```

## Advanced Load Testing Scenarios

### Mixed Workload Testing

Simulate real-world usage patterns with different user types:

```python
# tests/load_testing/mixed_workload_test.py
from locust import HttpUser, task, between
import random

class RegularUser(HttpUser):
    weight = 70  # 70% of users are regular users
    wait_time = between(45, 90)
    
    @task(5)
    def search_cases(self):
        response = self.client.post("/search", json={
            "query": "common user issue",
            "top_k": 5
        })
        
    @task(1)
    def check_status(self):
        response = self.client.get("/health")

class PowerUser(HttpUser):
    weight = 20  # 20% are power users (support agents)
    wait_time = between(10, 30)
    
    @task(10)
    def intensive_search(self):
        response = self.client.post("/search", json={
            "query": "technical troubleshooting",
            "top_k": 20,
            "similarity_threshold": 0.6
        })
        
    @task(2)
    def admin_operations(self):
        endpoints = ["/sync/status", "/performance/report"]
        endpoint = random.choice(endpoints)
        response = self.client.get(endpoint)

class AdminUser(HttpUser):
    weight = 10  # 10% are admin users
    wait_time = between(120, 300)
    
    @task(3)
    def monitor_system(self):
        response = self.client.get("/health/detailed")
        
    @task(2)
    def manage_scheduler(self):
        response = self.client.get("/scheduler/jobs")
        
    @task(1)
    def trigger_maintenance(self):
        response = self.client.post("/sync/manual")
```

### Geographic Distribution Testing

Simulate users from different locations with varying latency:

```python
# tests/load_testing/geographic_test.py
from locust import HttpUser, task, between
import time
import random

class USEastUser(HttpUser):
    weight = 40
    
    def on_start(self):
        # Simulate low latency (East Coast)
        self.latency_ms = random.uniform(20, 50)
        
    @task
    def search_with_latency(self):
        time.sleep(self.latency_ms / 1000)  # Simulate network latency
        response = self.client.post("/search", json={
            "query": "server issues east coast",
            "top_k": 10
        })

class EuropeUser(HttpUser):
    weight = 30
    
    def on_start(self):
        # Simulate medium latency (Europe)
        self.latency_ms = random.uniform(80, 150)
        
    @task
    def search_with_latency(self):
        time.sleep(self.latency_ms / 1000)
        response = self.client.post("/search", json={
            "query": "network problems europe",
            "top_k": 10
        })

class APACUser(HttpUser):
    weight = 30
    
    def on_start(self):
        # Simulate high latency (Asia-Pacific)
        self.latency_ms = random.uniform(150, 300)
        
    @task
    def search_with_latency(self):
        time.sleep(self.latency_ms / 1000)
        response = self.client.post("/search", json={
            "query": "system outage apac",
            "top_k": 10
        })
```

## Performance Monitoring During Load Tests

### Custom Metrics Collection

```python
# tests/load_testing/monitored_load_test.py
from locust import HttpUser, task, between, events
import time
import psutil
import logging

# Setup logging for performance metrics
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MonitoredUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def monitored_search(self):
        start_time = time.time()
        response = self.client.post("/search", json={
            "query": "monitored search query",
            "top_k": 10
        })
        duration = time.time() - start_time
        
        # Log custom metrics
        logger.info(f"Search duration: {duration:.3f}s, "
                   f"Status: {response.status_code}, "
                   f"Memory: {psutil.virtual_memory().percent}%")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize monitoring when test starts."""
    logger.info("Load test started - beginning performance monitoring")

@events.test_stop.add_listener  
def on_test_stop(environment, **kwargs):
    """Finalize monitoring when test stops."""
    logger.info("Load test completed - performance monitoring ended")

@events.request.add_listener
def record_performance(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Record performance metrics for each request."""
    if exception:
        logger.error(f"Request failed: {name} - {exception}")
    else:
        logger.info(f"Request success: {name} - {response_time}ms")
```

### Resource Monitoring Script

Create a separate monitoring script to track system resources:

```python
# tests/load_testing/resource_monitor.py
import psutil
import time
import json
import sys
from datetime import datetime

def monitor_resources(duration_seconds=3600, interval=10):
    """Monitor system resources during load test."""
    
    metrics = []
    start_time = time.time()
    
    print(f"Starting resource monitoring for {duration_seconds} seconds...")
    
    while time.time() - start_time < duration_seconds:
        timestamp = datetime.now().isoformat()
        
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        # Disk I/O
        disk_io = psutil.disk_io_counters()
        
        # Network I/O  
        network_io = psutil.net_io_counters()
        
        metric = {
            'timestamp': timestamp,
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024**3),
            'disk_read_mb': disk_io.read_bytes / (1024**2),
            'disk_write_mb': disk_io.write_bytes / (1024**2),
            'network_sent_mb': network_io.bytes_sent / (1024**2),
            'network_recv_mb': network_io.bytes_recv / (1024**2)
        }
        
        metrics.append(metric)
        print(f"CPU: {cpu_percent:5.1f}%, Memory: {memory.percent:5.1f}%, "
              f"Disk R/W: {disk_io.read_bytes/(1024**2):6.1f}/{disk_io.write_bytes/(1024**2):6.1f} MB")
        
        time.sleep(interval)
    
    # Save metrics to file
    with open('load_test_metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    
    print(f"Resource monitoring completed. Metrics saved to load_test_metrics.json")

if __name__ == "__main__":
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 3600
    monitor_resources(duration)
```

**Usage:**
```bash
# Start resource monitoring (in separate terminal)
python tests/load_testing/resource_monitor.py 7200  # 2 hours

# Start load test
locust -f tests/load_testing/steady_state_test.py --host=http://localhost:8008
```

## Distributed Load Testing

For testing at very high scale, distribute load across multiple machines:

### Master Configuration

```bash
# On master machine
locust -f tests/load_testing/steady_state_test.py \
  --host=http://localhost:8008 \
  --master \
  --master-bind-host=0.0.0.0 \
  --master-bind-port=5557
```

### Worker Configuration

```bash
# On worker machines  
locust -f tests/load_testing/steady_state_test.py \
  --host=http://localhost:8008 \
  --worker \
  --master-host=<master-ip>
```

## Load Test Execution Plans

### Daily Load Test Schedule

```bash
#!/bin/bash
# tests/load_testing/daily_test_schedule.sh

echo "Starting daily load test schedule..."

# Morning: Steady state test (8 hours)
echo "$(date): Starting steady state test"
locust -f tests/load_testing/steady_state_test.py \
  --host=http://localhost:8008 \
  --users=50 --spawn-rate=5 --run-time=8h \
  --headless --html=reports/morning_steady_$(date +%Y%m%d).html

# Afternoon: Peak load test (2 hours)  
echo "$(date): Starting peak load test"
locust -f tests/load_testing/peak_load_test.py \
  --host=http://localhost:8008 \
  --users=200 --spawn-rate=20 --run-time=2h \
  --headless --html=reports/afternoon_peak_$(date +%Y%m%d).html

# Evening: Mixed workload test (4 hours)
echo "$(date): Starting mixed workload test"
locust -f tests/load_testing/mixed_workload_test.py \
  --host=http://localhost:8008 \
  --users=100 --spawn-rate=10 --run-time=4h \
  --headless --html=reports/evening_mixed_$(date +%Y%m%d).html

echo "$(date): Daily load test schedule completed"
```

### Weekly Soak Test

```bash
#!/bin/bash
# tests/load_testing/weekly_soak_test.sh

echo "Starting weekly soak test..."

# Start resource monitoring
python tests/load_testing/resource_monitor.py 604800 &  # 7 days
MONITOR_PID=$!

# Run soak test for 7 days
locust -f tests/load_testing/soak_test.py \
  --host=http://localhost:8008 \
  --users=25 --spawn-rate=2 --run-time=168h \
  --headless --html=reports/weekly_soak_$(date +%Y%m%d).html

# Stop resource monitoring
kill $MONITOR_PID

echo "Weekly soak test completed"
```

## Performance Benchmarks and Targets

### Response Time Targets

| Operation | Target (ms) | Acceptable (ms) | Maximum (ms) |
|-----------|-------------|-----------------|--------------|
| Single search | < 50 | < 100 | < 200 |
| Health check | < 10 | < 25 | < 50 |
| Sync status | < 100 | < 200 | < 500 |
| Manual sync trigger | < 500 | < 1000 | < 2000 |

### Throughput Targets

| Load Scenario | Target RPS | Acceptable RPS | Minimum RPS |
|---------------|------------|----------------|-------------|
| Steady state | 20-30 | 15-20 | 10 |
| Peak load | 100-150 | 75-100 | 50 |
| Search-heavy | 50-75 | 30-50 | 20 |

### Resource Usage Limits

| Resource | Target | Acceptable | Maximum |
|----------|--------|------------|---------|
| CPU Usage | < 50% | < 70% | < 85% |
| Memory Usage | < 60% | < 80% | < 90% |
| Disk I/O | < 50% | < 70% | < 85% |

## Analyzing Load Test Results

### Locust Report Analysis

Key metrics to monitor in Locust reports:

1. **Response Times**: 50th, 95th, 99th percentiles
2. **Request Rate**: Requests per second sustained
3. **Failure Rate**: Percentage of failed requests
4. **Concurrent Users**: Maximum users handled successfully

### Custom Analysis Scripts

```python
# tests/load_testing/analyze_results.py
import json
import pandas as pd
import matplotlib.pyplot as plt

def analyze_load_test_results(metrics_file, locust_stats_file):
    """Analyze load test results and generate reports."""
    
    # Load resource metrics
    with open(metrics_file, 'r') as f:
        metrics = json.load(f)
    
    df = pd.DataFrame(metrics)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Generate plots
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # CPU Usage
    axes[0,0].plot(df['timestamp'], df['cpu_percent'])
    axes[0,0].set_title('CPU Usage Over Time')
    axes[0,0].set_ylabel('CPU %')
    
    # Memory Usage
    axes[0,1].plot(df['timestamp'], df['memory_percent'])
    axes[0,1].set_title('Memory Usage Over Time')
    axes[0,1].set_ylabel('Memory %')
    
    # Disk I/O
    axes[1,0].plot(df['timestamp'], df['disk_read_mb'], label='Read')
    axes[1,0].plot(df['timestamp'], df['disk_write_mb'], label='Write')
    axes[1,0].set_title('Disk I/O Over Time')
    axes[1,0].set_ylabel('MB')
    axes[1,0].legend()
    
    # Network I/O
    axes[1,1].plot(df['timestamp'], df['network_sent_mb'], label='Sent')
    axes[1,1].plot(df['timestamp'], df['network_recv_mb'], label='Received')
    axes[1,1].set_title('Network I/O Over Time')
    axes[1,1].set_ylabel('MB')
    axes[1,1].legend()
    
    plt.tight_layout()
    plt.savefig('load_test_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    # Generate summary report
    summary = {
        'test_duration_hours': len(df) * 10 / 3600,  # 10-second intervals
        'avg_cpu_percent': df['cpu_percent'].mean(),
        'max_cpu_percent': df['cpu_percent'].max(),
        'avg_memory_percent': df['memory_percent'].mean(),
        'max_memory_percent': df['memory_percent'].max(),
        'total_disk_read_gb': df['disk_read_mb'].iloc[-1] / 1024,
        'total_disk_write_gb': df['disk_write_mb'].iloc[-1] / 1024
    }
    
    print("Load Test Summary:")
    print(f"Duration: {summary['test_duration_hours']:.1f} hours")
    print(f"Average CPU: {summary['avg_cpu_percent']:.1f}%")
    print(f"Peak CPU: {summary['max_cpu_percent']:.1f}%")
    print(f"Average Memory: {summary['avg_memory_percent']:.1f}%")
    print(f"Peak Memory: {summary['max_memory_percent']:.1f}%")
    
    return summary

# Usage
# summary = analyze_load_test_results('load_test_metrics.json', 'locust_stats.json')
```

## Troubleshooting Load Tests

### Common Issues

**High Response Times:**
```bash
# Check if API server is running
curl http://localhost:8008/health

# Monitor server logs
tail -f logs/api.log

# Check system resources
htop
```

**Connection Errors:**
```bash
# Increase system limits
ulimit -n 65536

# Check network connections
netstat -an | grep 8008
```

**Memory Issues:**
```bash
# Monitor memory usage
free -h
watch -n 1 'free -h'

# Check for memory leaks
python -m memory_profiler scripts/run_api.py
```

### Load Test Debugging

Enable debug logging in Locust:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

class DebugUser(HttpUser):
    @task
    def debug_search(self):
        response = self.client.post("/search", json={"query": "test"})
        print(f"Response: {response.status_code}, Time: {response.elapsed}")
```

This comprehensive load testing guide provides the framework and tools needed to validate the KMS-SFDC system's performance at scale, ensuring it can handle 3000+ tickets per day and peak load scenarios effectively.