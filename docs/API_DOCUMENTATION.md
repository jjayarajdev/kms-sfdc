# KMS-SFDC API Documentation

Complete REST API reference for the KMS-SFDC Vector Database system.

## Base URL

```
http://localhost:8008
```

## Authentication

Currently, the API uses no authentication for development. For production deployment, implement API key or JWT token authentication.

## Content Types

All endpoints accept and return `application/json` unless otherwise specified.

---

## 🔍 Search Endpoints

### POST /search

Search for similar cases using vector similarity.

**Request Body:**
```json
{
  "query": "user login issues with SSO",
  "top_k": 10,
  "similarity_threshold": 0.7
}
```

**Parameters:**
- `query` (string, required): Search query text (1-1000 characters)
- `top_k` (integer, optional): Number of results to return (1-100, default: 10)
- `similarity_threshold` (float, optional): Minimum similarity score (0.0-1.0, default: 0.0)

**Response:**
```json
{
  "query": "user login issues with SSO",
  "results": [
    {
      "similarity_score": 0.89,
      "case_id": "5003g00000123ABC",
      "case_number": "00012345",
      "subject_description": "SSO login failure",
      "description_description": "User cannot login via SSO",
      "issue_plain_text": "Authentication error",
      "cause_plain_text": "SSO configuration issue",
      "resolution_plain_text": "Updated SSO settings",
      "status_text": "Closed",
      "textbody": "Full case description...",
      "created_date": "2024-01-15T10:30:00Z",
      "preview_text": "SSO login failure for user..."
    }
  ],
  "total_results": 1,
  "search_time_ms": 45.67
}
```

### GET /search

Alternative GET endpoint for simple searches.

**Query Parameters:**
- `q` (string, required): Search query text
- `top_k` (integer, optional): Number of results to return
- `threshold` (float, optional): Similarity threshold

**Example:**
```bash
curl "http://localhost:8008/search?q=password%20reset&top_k=5&threshold=0.7"
```

---

## 💊 Health & Status Endpoints

### GET /health

Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "vector_db_ready": true,
  "total_vectors": 15432,
  "model_name": "nomic-embed-text-v1.5"
}
```

### GET /health/detailed

Detailed health check with system metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "vector_db": {
    "ready": true,
    "total_vectors": 15432,
    "index_size_mb": 245.6
  },
  "system": {
    "cpu_percent": 12.5,
    "memory_percent": 34.2,
    "disk_free_gb": 102.4
  },
  "api": {
    "requests_per_minute": 23,
    "average_response_time_ms": 45.2,
    "error_rate_percent": 0.1
  }
}
```

### GET /health/report

Health report for specified time period.

**Query Parameters:**
- `hours` (integer, optional): Hours to include in report (default: 24)

**Response:**
```json
{
  "period_hours": 24,
  "total_requests": 1456,
  "average_response_time_ms": 42.3,
  "error_count": 2,
  "uptime_percent": 99.98,
  "performance_summary": {
    "fastest_response_ms": 12,
    "slowest_response_ms": 234,
    "p95_response_time_ms": 78
  }
}
```

### GET /stats

Vector database statistics.

**Response:**
```json
{
  "is_trained": true,
  "total_vectors": 15432,
  "model_name": "nomic-embed-text-v1.5",
  "index_type": "IndexFlatIP",
  "dimension": 768,
  "memory_usage_mb": 245.6,
  "last_updated": "2024-01-15T09:15:00Z"
}
```

---

## 📅 Scheduler Endpoints

### GET /scheduler/jobs

Get all scheduled jobs with their status.

**Response:**
```json
[
  {
    "id": "sfdc_sync",
    "name": "SFDC Data Sync",
    "description": "Synchronize new and updated cases from Salesforce",
    "enabled": true,
    "schedule": {
      "type": "interval",
      "interval_minutes": 60
    },
    "last_run": "2024-01-15T09:00:00Z",
    "next_run": "2024-01-15T10:00:00Z",
    "status": "completed",
    "last_success": "2024-01-15T09:00:00Z",
    "last_error": null
  }
]
```

### GET /scheduler/jobs/{job_id}

Get status of a specific job.

**Response:**
```json
{
  "id": "sfdc_sync",
  "name": "SFDC Data Sync",
  "description": "Synchronize new and updated cases from Salesforce",
  "enabled": true,
  "schedule": {
    "type": "interval",
    "interval_minutes": 60
  },
  "last_run": "2024-01-15T09:00:00Z",
  "next_run": "2024-01-15T10:00:00Z",
  "status": "completed",
  "last_success": "2024-01-15T09:00:00Z",
  "last_error": null
}
```

### PUT /scheduler/jobs/{job_id}

Update job schedule configuration.

**Request Body:**
```json
{
  "enabled": true,
  "schedule": {
    "type": "interval",
    "interval_minutes": 120
  }
}
```

**Schedule Types:**

1. **Interval-based:**
```json
{
  "type": "interval",
  "interval_minutes": 60
}
```

2. **Daily scheduling:**
```json
{
  "type": "daily",
  "time": "02:00"
}
```

3. **Cron expressions:**
```json
{
  "type": "cron",
  "expression": "0 */2 * * *"
}
```

**Response:**
```json
{
  "status": "updated",
  "job_id": "sfdc_sync"
}
```

### POST /scheduler/jobs/{job_id}/trigger

Manually trigger a job execution.

**Response:**
```json
{
  "status": "triggered",
  "job_id": "sfdc_sync"
}
```

---

## 🔄 Sync Endpoints

### GET /sync/status

Get current synchronization status and statistics.

**Response:**
```json
{
  "stats": {
    "last_sync": "2024-01-15T09:00:00Z",
    "last_successful_sync": "2024-01-15T09:00:00Z",
    "total_cases_synced": 15432,
    "total_cases_in_index": 15432,
    "average_cases_per_sync": 234.5,
    "average_sync_duration_seconds": 125.3
  },
  "validation": {
    "is_valid": true,
    "checks": {
      "sfdc_connection": true,
      "vector_db_loaded": true,
      "total_vectors": 15432,
      "hours_since_last_sync": 1.2
    },
    "warnings": [],
    "errors": []
  },
  "scheduler_running": true
}
```

### POST /sync/manual

Trigger a manual synchronization.

**Request Body (optional):**
```json
{
  "start_date": "2024-01-14",
  "end_date": "2024-01-15"
}
```

**Response:**
```json
{
  "status": "triggered",
  "message": "Manual sync has been triggered. Check /sync/status for progress."
}
```

### GET /sync/history

Get synchronization history.

**Query Parameters:**
- `limit` (integer, optional): Number of entries to return (1-100, default: 10)

**Response:**
```json
{
  "history": [
    {
      "timestamp": "2024-01-15T09:00:00Z",
      "cases_processed": 125,
      "cases_added": 123,
      "duration_seconds": 120.5
    }
  ],
  "total_syncs": 45,
  "total_cases_synced": 15432
}
```

---

## 📊 Performance Endpoints

### GET /performance/report

Get comprehensive performance report.

**Response:**
```json
{
  "report_generated": "2024-01-15T10:30:00Z",
  "system_performance": {
    "cpu_usage_percent": 12.5,
    "memory_usage_percent": 34.2,
    "disk_usage_percent": 67.8
  },
  "api_performance": {
    "total_requests": 1456,
    "requests_per_minute": 23.4,
    "average_response_time_ms": 42.3,
    "error_rate_percent": 0.1
  },
  "vector_operations": {
    "embeddings_generated": 234,
    "average_embedding_time_ms": 15.6,
    "searches_performed": 1222,
    "average_search_time_ms": 8.9
  }
}
```

### GET /performance/operations

Get performance statistics for operations.

**Query Parameters:**
- `operation` (string, optional): Specific operation name

**Response:**
```json
{
  "operations": {
    "vector_search": {
      "count": 1222,
      "average_duration_ms": 8.9,
      "min_duration_ms": 2.1,
      "max_duration_ms": 45.6,
      "p95_duration_ms": 18.2
    },
    "text_embedding": {
      "count": 234,
      "average_duration_ms": 15.6,
      "min_duration_ms": 8.2,
      "max_duration_ms": 67.3,
      "p95_duration_ms": 32.1
    }
  }
}
```

### GET /performance/recommendations

Get performance optimization recommendations.

**Response:**
```json
{
  "recommendations": [
    {
      "category": "memory",
      "priority": "medium",
      "issue": "Memory usage is 85% of available",
      "recommendation": "Consider increasing batch size or available memory"
    },
    {
      "category": "search",
      "priority": "low", 
      "issue": "95th percentile search time is 45ms",
      "recommendation": "Search performance is within acceptable limits"
    }
  ],
  "overall_health": "good"
}
```

### POST /performance/save

Save current performance metrics to disk.

**Response:**
```json
{
  "status": "saved",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## 🛠️ Admin Endpoints

### POST /rebuild-index

Trigger index rebuild (admin endpoint).

**Response:**
```json
{
  "message": "Index rebuild triggered",
  "status": "started",
  "note": "This operation runs in background. Check /health for completion status."
}
```

---

## Error Responses

All endpoints return consistent error responses:

**Format:**
```json
{
  "detail": "Error message describing what went wrong"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `404` - Not Found (resource doesn't exist)
- `422` - Validation Error (invalid request body)
- `500` - Internal Server Error
- `503` - Service Unavailable (vector DB not ready)

**Example Error Response:**
```json
{
  "detail": "Vector database not ready. Index needs to be built."
}
```

---

## Rate Limiting

Currently no rate limiting is implemented. For production deployment, consider implementing rate limiting based on:
- Requests per minute per IP
- Requests per minute per API key
- Special limits for resource-intensive operations (rebuild-index, manual sync)

---

## OpenAPI Documentation

Interactive API documentation is available at:
- **Swagger UI**: `http://localhost:8008/docs`
- **ReDoc**: `http://localhost:8008/redoc`
- **OpenAPI JSON**: `http://localhost:8008/openapi.json`