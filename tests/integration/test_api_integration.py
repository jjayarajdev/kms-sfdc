"""
Integration tests for API endpoints.
"""

import pytest
import os
import tempfile
import json
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from src.search.api import app


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for the complete API workflow."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)

    @patch('src.search.api.vector_db')
    @patch('src.search.api.health_monitor')
    @patch('src.search.api.metrics_collector')
    def test_complete_api_workflow(self, mock_metrics, mock_health, mock_vector_db, client):
        """Test complete API workflow from health check to search."""
        # Setup mocks
        mock_vector_db.get_stats.return_value = {
            'is_trained': True,
            'total_vectors': 1000,
            'model_name': 'test-model'
        }
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = [
            {
                'similarity_score': 0.95,
                'case_id': 'case_001',
                'case_number': 'CASE-001',
                'subject_description': 'Server crash',
                'description_description': 'Server crashed unexpectedly',
                'issue_plain_text': 'Server issue',
                'cause_plain_text': 'Hardware failure',
                'resolution_plain_text': 'Replaced hardware',
                'status_text': 'Closed',
                'textbody': 'Additional details',
                'created_date': '2024-01-01T10:00:00Z',
                'preview_text': 'Server crash...'
            }
        ]
        
        mock_health.check_health.return_value = {
            'status': 'healthy',
            'cpu_usage': 45.0,
            'memory_usage': 60.0
        }
        
        # Step 1: Check system health
        health_response = client.get("/health")
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data['status'] == 'healthy'
        assert health_data['vector_db_ready'] is True
        
        # Step 2: Get system stats
        stats_response = client.get("/stats")
        assert stats_response.status_code == 200
        stats_data = stats_response.json()
        assert stats_data['is_trained'] is True
        assert stats_data['total_vectors'] == 1000
        
        # Step 3: Perform search
        search_request = {
            "query": "server crash",
            "top_k": 5,
            "similarity_threshold": 0.7
        }
        
        search_response = client.post("/search", json=search_request)
        assert search_response.status_code == 200
        search_data = search_response.json()
        
        assert search_data['query'] == 'server crash'
        assert search_data['total_results'] == 1
        assert len(search_data['results']) == 1
        assert 'search_time_ms' in search_data
        
        result = search_data['results'][0]
        assert result['similarity_score'] == 0.95
        assert result['case_id'] == 'case_001'
        assert result['subject_description'] == 'Server crash'
        
        # Step 4: Get detailed health check
        detailed_health_response = client.get("/health/detailed")
        assert detailed_health_response.status_code == 200
        detailed_health_data = detailed_health_response.json()
        assert detailed_health_data['status'] == 'healthy'

    @patch('src.search.api.vector_db')
    def test_api_error_handling_workflow(self, mock_vector_db, client):
        """Test API error handling workflow."""
        # Test when vector DB is not ready
        mock_vector_db.is_trained = False
        
        search_request = {"query": "test query"}
        response = client.post("/search", json=search_request)
        
        assert response.status_code == 503
        error_data = response.json()
        assert 'Vector database not ready' in error_data['detail']

    @patch('src.search.api.vector_db')
    def test_api_search_parameter_validation(self, mock_vector_db, client):
        """Test API search parameter validation."""
        mock_vector_db.is_trained = True
        
        # Test missing query
        response = client.post("/search", json={})
        assert response.status_code == 422
        
        # Test invalid top_k
        response = client.post("/search", json={
            "query": "test",
            "top_k": 0
        })
        assert response.status_code == 422
        
        # Test invalid similarity_threshold
        response = client.post("/search", json={
            "query": "test",
            "similarity_threshold": 1.5
        })
        assert response.status_code == 422
        
        # Test empty query
        response = client.post("/search", json={"query": ""})
        assert response.status_code == 422

    @patch('src.search.api.vector_db')
    def test_api_get_search_endpoint(self, mock_vector_db, client):
        """Test GET search endpoint."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = [
            {
                'similarity_score': 0.85,
                'case_id': 'case_002',
                'case_number': 'CASE-002',
                'subject_description': 'Database timeout',
                'description_description': 'Database connection timeout',
                'issue_plain_text': 'Connection issue',
                'cause_plain_text': 'Network latency',
                'resolution_plain_text': 'Optimized queries',
                'status_text': 'Resolved',
                'textbody': 'Database details',
                'created_date': '2024-01-02T14:30:00Z',
                'preview_text': 'Database timeout...'
            }
        ]
        
        # Test GET request with parameters
        response = client.get("/search?q=database timeout&top_k=3&threshold=0.8")
        
        assert response.status_code == 200
        data = response.json()
        assert data['query'] == 'database timeout'
        assert len(data['results']) == 1
        
        # Verify vector_db.search was called with correct parameters
        mock_vector_db.search.assert_called_with(
            query_text="database timeout",
            top_k=3,
            similarity_threshold=0.8
        )

    @patch('src.search.api.vector_db')
    def test_api_concurrent_requests(self, mock_vector_db, client):
        """Test API handling of concurrent requests."""
        import concurrent.futures
        import time
        
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = [
            {
                'similarity_score': 0.75,
                'case_id': 'case_concurrent',
                'case_number': 'CASE-CONCURRENT',
                'subject_description': 'Concurrent test',
                'description_description': 'Test concurrent requests',
                'issue_plain_text': 'Concurrent issue',
                'cause_plain_text': 'Load testing',
                'resolution_plain_text': 'Handled successfully',
                'status_text': 'Closed',
                'textbody': 'Concurrent test details',
                'created_date': '2024-01-01T10:00:00Z',
                'preview_text': 'Concurrent test...'
            }
        ]
        
        def make_search_request(query_id):
            return client.post("/search", json={
                "query": f"concurrent test {query_id}",
                "top_k": 1
            })
        
        # Make 10 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_search_request, i) for i in range(10)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert len(data['results']) == 1

    @patch('src.search.api.vector_db')
    @patch('src.search.api.health_monitor')
    def test_api_monitoring_integration(self, mock_health, mock_vector_db, client):
        """Test API integration with monitoring systems."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = []
        
        # Mock monitoring systems
        mock_health.check_health.return_value = {
            'status': 'healthy',
            'system_metrics': {'cpu_usage': 45.0},
            'performance_metrics': {'avg_response_time': 120.5},
            'alerts': []
        }
        
        mock_health.get_health_report.return_value = {
            'period_hours': 24,
            'total_requests': 1000,
            'avg_response_time': 125.0,
            'error_rate': 0.01
        }
        
        mock_health.get_metrics_summary.return_value = {
            'active_connections': 15,
            'requests_per_minute': 25.0
        }
        
        # Test health endpoints
        response = client.get("/health/detailed")
        assert response.status_code == 200
        detailed_health = response.json()
        assert detailed_health['status'] == 'healthy'
        
        response = client.get("/health/report?hours=24")
        assert response.status_code == 200
        report = response.json()
        assert report['period_hours'] == 24
        assert report['total_requests'] == 1000
        
        response = client.get("/health/metrics")
        assert response.status_code == 200
        metrics = response.json()
        assert metrics['active_connections'] == 15

    @patch('src.search.api.metrics_collector')
    def test_api_performance_monitoring_integration(self, mock_metrics, client):
        """Test API integration with performance monitoring."""
        # Mock performance metrics
        mock_metrics.get_performance_report.return_value = {
            'operation_stats': {
                'vector_search': {
                    'total_calls': 500,
                    'avg_time_ms': 45.2,
                    'success_rate': 0.98
                }
            },
            'batch_processing': {
                'total_batches': 20,
                'avg_batch_size': 25
            }
        }
        
        mock_metrics.get_operation_stats.return_value = {
            'total_calls': 500,
            'avg_time_ms': 45.2,
            'min_time_ms': 12.5,
            'max_time_ms': 180.3,
            'success_rate': 0.98
        }
        
        mock_metrics.get_batch_processing_summary.return_value = {
            'total_batches': 20,
            'avg_batch_size': 25,
            'throughput_records_per_sec': 10.2
        }
        
        mock_metrics.get_optimization_recommendations.return_value = [
            "Consider increasing batch size for better throughput",
            "Enable GPU acceleration for faster embeddings"
        ]
        
        # Test performance endpoints
        response = client.get("/performance/report")
        assert response.status_code == 200
        report = response.json()
        assert 'operation_stats' in report
        assert 'batch_processing' in report
        
        response = client.get("/performance/operations?operation=vector_search")
        assert response.status_code == 200
        stats = response.json()
        assert stats['total_calls'] == 500
        
        response = client.get("/performance/batch")
        assert response.status_code == 200
        batch_stats = response.json()
        assert batch_stats['total_batches'] == 20
        
        response = client.get("/performance/recommendations")
        assert response.status_code == 200
        recommendations = response.json()
        assert len(recommendations) == 2
        
        # Test saving metrics
        response = client.post("/performance/save")
        assert response.status_code == 200
        save_result = response.json()
        assert save_result['status'] == 'saved'
        mock_metrics.save_metrics.assert_called_once()

    @patch('src.search.api.vector_db')
    def test_api_search_result_structure(self, mock_vector_db, client):
        """Test API search result structure compliance."""
        mock_vector_db.is_trained = True
        
        # Mock complete search result with all required fields
        complete_result = {
            'similarity_score': 0.92,
            'case_id': 'case_complete',
            'case_number': 'CASE-COMPLETE',
            'subject_description': 'Complete test case',
            'description_description': 'Complete description',
            'issue_plain_text': 'Complete issue description',
            'cause_plain_text': 'Complete cause analysis',
            'resolution_plain_text': 'Complete resolution steps',
            'status_text': 'Resolved',
            'textbody': 'Complete additional text',
            'created_date': '2024-01-01T10:00:00Z',
            'preview_text': 'Complete preview text...'
        }
        
        mock_vector_db.search.return_value = [complete_result]
        
        response = client.post("/search", json={"query": "complete test"})
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert 'query' in data
        assert 'results' in data
        assert 'total_results' in data
        assert 'search_time_ms' in data
        
        result = data['results'][0]
        
        # Verify all expected fields are present
        expected_fields = [
            'similarity_score', 'case_id', 'case_number', 'subject_description',
            'description_description', 'issue_plain_text', 'cause_plain_text',
            'resolution_plain_text', 'status_text', 'textbody', 'created_date',
            'preview_text'
        ]
        
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"
            assert result[field] == complete_result[field]

    def test_api_openapi_schema(self, client):
        """Test API OpenAPI schema generation."""
        response = client.get("/openapi.json")
        
        assert response.status_code == 200
        schema = response.json()
        
        # Verify basic OpenAPI structure
        assert 'openapi' in schema
        assert 'info' in schema
        assert 'paths' in schema
        
        # Verify key endpoints are documented
        paths = schema['paths']
        assert '/search' in paths
        assert '/health' in paths
        assert '/stats' in paths
        
        # Verify search endpoint has proper schema
        search_endpoint = paths['/search']
        assert 'post' in search_endpoint
        assert 'get' in search_endpoint
        
        # Verify request/response schemas
        post_schema = search_endpoint['post']
        assert 'requestBody' in post_schema
        assert 'responses' in post_schema

    @patch('src.search.api.vector_db')
    def test_api_cors_integration(self, mock_vector_db, client):
        """Test CORS headers in API responses."""
        mock_vector_db.get_stats.return_value = {
            'is_trained': True,
            'total_vectors': 100
        }
        
        # Test preflight request
        response = client.options("/health")
        
        # CORS should be configured (exact behavior depends on FastAPI CORS middleware)
        assert response.status_code in [200, 405]  # 405 if OPTIONS not implemented
        
        # Test actual request has CORS headers (if configured)
        response = client.get("/health")
        assert response.status_code == 200

    @patch('src.search.api.vector_db')
    def test_api_large_response_handling(self, mock_vector_db, client):
        """Test API handling of large responses."""
        mock_vector_db.is_trained = True
        
        # Create large mock result set
        large_results = []
        for i in range(50):
            large_results.append({
                'similarity_score': 0.8 - (i * 0.01),
                'case_id': f'case_{i:03d}',
                'case_number': f'CASE-{i:03d}',
                'subject_description': f'Large dataset test case {i}' * 10,
                'description_description': f'Long description for case {i}' * 20,
                'issue_plain_text': f'Issue description {i}' * 15,
                'cause_plain_text': f'Cause analysis {i}' * 10,
                'resolution_plain_text': f'Resolution steps {i}' * 25,
                'status_text': 'Closed',
                'textbody': f'Additional text {i}' * 30,
                'created_date': '2024-01-01T10:00:00Z',
                'preview_text': f'Preview text {i}' * 10
            })
        
        mock_vector_db.search.return_value = large_results
        
        response = client.post("/search", json={
            "query": "large dataset test",
            "top_k": 50
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['total_results'] == 50
        assert len(data['results']) == 50
        
        # Verify response is properly structured even with large data
        assert 'search_time_ms' in data
        assert isinstance(data['search_time_ms'], (int, float))

    def test_api_admin_endpoints(self, client):
        """Test admin endpoints functionality."""
        # Test rebuild index endpoint
        response = client.post("/rebuild-index")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'started'
        assert 'message' in data

    @patch('src.search.api.vector_db')
    @patch('src.search.api.health_monitor')
    def test_api_error_recovery_workflow(self, mock_health, mock_vector_db, client):
        """Test API error recovery workflow."""
        # Simulate temporary error
        mock_vector_db.is_trained = True
        mock_vector_db.search.side_effect = [
            Exception("Temporary search error"),
            [{'similarity_score': 0.8, 'case_id': 'recovered'}]  # Recovery
        ]
        
        # First request should fail
        response1 = client.post("/search", json={"query": "test"})
        assert response1.status_code == 500
        
        # Reset side effect for recovery
        mock_vector_db.search.side_effect = None
        mock_vector_db.search.return_value = [{
            'similarity_score': 0.8,
            'case_id': 'recovered',
            'case_number': 'CASE-RECOVERED',
            'subject_description': 'Recovered case',
            'description_description': 'System recovered',
            'issue_plain_text': 'Recovery test',
            'cause_plain_text': 'System error',
            'resolution_plain_text': 'System restored',
            'status_text': 'Resolved',
            'textbody': 'Recovery details',
            'created_date': '2024-01-01T10:00:00Z',
            'preview_text': 'Recovered case...'
        }]
        
        # Second request should succeed
        response2 = client.post("/search", json={"query": "test"})
        assert response2.status_code == 200
        data = response2.json()
        assert data['results'][0]['case_id'] == 'recovered'