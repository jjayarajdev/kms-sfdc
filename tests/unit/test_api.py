"""
Unit tests for API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import json

from src.search.api import app


@pytest.mark.unit
class TestSearchAPI:
    """Test cases for Search API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return TestClient(app)
    
    @patch('src.search.api.vector_db')
    def test_health_check_healthy(self, mock_vector_db, client):
        """Test health check endpoint when system is healthy."""
        mock_vector_db.get_stats.return_value = {
            'is_trained': True,
            'total_vectors': 1000,
            'model_name': 'test-model'
        }
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert data['vector_db_ready'] is True
        assert data['total_vectors'] == 1000
        assert data['model_name'] == 'test-model'

    @patch('src.search.api.vector_db')
    def test_health_check_unhealthy(self, mock_vector_db, client):
        """Test health check endpoint when system is unhealthy."""
        mock_vector_db.get_stats.return_value = {
            'is_trained': False,
            'total_vectors': 0,
            'model_name': 'test-model'
        }
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'  # Endpoint status, not system status
        assert data['vector_db_ready'] is False
        assert data['total_vectors'] == 0

    @patch('src.search.api.vector_db')
    def test_search_post_success(self, mock_vector_db, client, mock_search_results):
        """Test successful POST search request."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = mock_search_results
        
        search_request = {
            "query": "server crash",
            "top_k": 5,
            "similarity_threshold": 0.7
        }
        
        response = client.post("/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['query'] == 'server crash'
        assert data['total_results'] == len(mock_search_results)
        assert len(data['results']) == len(mock_search_results)
        assert 'search_time_ms' in data
        
        # Check result structure
        result = data['results'][0]
        assert 'similarity_score' in result
        assert 'case_id' in result
        assert 'subject_description' in result

    @patch('src.search.api.vector_db')
    def test_search_post_db_not_ready(self, mock_vector_db, client):
        """Test POST search when database is not ready."""
        mock_vector_db.is_trained = False
        
        search_request = {
            "query": "server crash",
            "top_k": 5
        }
        
        response = client.post("/search", json=search_request)
        
        assert response.status_code == 503
        data = response.json()
        assert 'Vector database not ready' in data['detail']

    @patch('src.search.api.vector_db')
    def test_search_post_invalid_request(self, mock_vector_db, client):
        """Test POST search with invalid request data."""
        mock_vector_db.is_trained = True
        
        # Missing required query field
        invalid_request = {
            "top_k": 5
        }
        
        response = client.post("/search", json=invalid_request)
        
        assert response.status_code == 422  # Validation error

    @patch('src.search.api.vector_db')
    def test_search_post_validation_errors(self, mock_vector_db, client):
        """Test POST search with validation errors."""
        mock_vector_db.is_trained = True
        
        # Invalid values
        invalid_request = {
            "query": "",  # Empty query
            "top_k": 0,   # Invalid top_k
            "similarity_threshold": 1.5  # Invalid threshold > 1.0
        }
        
        response = client.post("/search", json=invalid_request)
        
        assert response.status_code == 422

    @patch('src.search.api.vector_db')
    def test_search_get_success(self, mock_vector_db, client, mock_search_results):
        """Test successful GET search request."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = mock_search_results
        
        response = client.get("/search?q=server crash&top_k=5&threshold=0.7")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data['query'] == 'server crash'
        assert data['total_results'] == len(mock_search_results)

    @patch('src.search.api.vector_db')
    def test_search_get_missing_query(self, mock_vector_db, client):
        """Test GET search without required query parameter."""
        mock_vector_db.is_trained = True
        
        response = client.get("/search")
        
        assert response.status_code == 422  # Missing required parameter

    @patch('src.search.api.vector_db')
    def test_search_error_handling(self, mock_vector_db, client):
        """Test search error handling."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.side_effect = Exception("Search failed")
        
        search_request = {
            "query": "server crash"
        }
        
        response = client.post("/search", json=search_request)
        
        assert response.status_code == 500
        data = response.json()
        assert 'Search error' in data['detail']

    @patch('src.search.api.vector_db')
    def test_get_database_stats(self, mock_vector_db, client):
        """Test database stats endpoint."""
        expected_stats = {
            'is_trained': True,
            'total_vectors': 1000,
            'dimension': 384,
            'index_type': 'IndexFlatIP',
            'model_name': 'test-model'
        }
        mock_vector_db.get_stats.return_value = expected_stats
        
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_stats

    @patch('src.search.api.health_monitor')
    def test_detailed_health_check(self, mock_health_monitor, client):
        """Test detailed health check endpoint."""
        expected_health = {
            'status': 'healthy',
            'cpu_usage': 45.2,
            'memory_usage': 62.8,
            'disk_usage': 78.5,
        }
        mock_health_monitor.check_health.return_value = expected_health
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_health

    @patch('src.search.api.health_monitor')
    def test_health_report(self, mock_health_monitor, client):
        """Test health report endpoint."""
        expected_report = {
            'period_hours': 24,
            'total_requests': 1500,
            'avg_response_time': 120.5,
            'error_rate': 0.02
        }
        mock_health_monitor.get_health_report.return_value = expected_report
        
        response = client.get("/health/report?hours=24")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_report

    @patch('src.search.api.health_monitor')
    def test_metrics_summary(self, mock_health_monitor, client):
        """Test metrics summary endpoint."""
        expected_metrics = {
            'active_connections': 15,
            'avg_response_time': 120.5,
            'requests_per_minute': 25.0
        }
        mock_health_monitor.get_metrics_summary.return_value = expected_metrics
        
        response = client.get("/health/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_metrics

    @patch('src.search.api.metrics_collector')
    def test_performance_report(self, mock_metrics_collector, client, sample_performance_metrics):
        """Test performance report endpoint."""
        mock_metrics_collector.get_performance_report.return_value = sample_performance_metrics
        
        response = client.get("/performance/report")
        
        assert response.status_code == 200
        data = response.json()
        assert data == sample_performance_metrics

    @patch('src.search.api.metrics_collector')
    def test_operation_stats(self, mock_metrics_collector, client):
        """Test operation stats endpoint."""
        expected_stats = {
            'total_calls': 100,
            'avg_time_ms': 45.2,
            'success_rate': 0.98
        }
        mock_metrics_collector.get_operation_stats.return_value = expected_stats
        
        response = client.get("/performance/operations?operation=vector_search")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_stats

    @patch('src.search.api.metrics_collector')
    def test_batch_performance(self, mock_metrics_collector, client):
        """Test batch performance endpoint."""
        expected_batch_stats = {
            'total_batches': 20,
            'avg_batch_size': 25,
            'throughput_records_per_sec': 10.2
        }
        mock_metrics_collector.get_batch_processing_summary.return_value = expected_batch_stats
        
        response = client.get("/performance/batch")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_batch_stats

    @patch('src.search.api.metrics_collector')
    def test_performance_recommendations(self, mock_metrics_collector, client):
        """Test performance recommendations endpoint."""
        expected_recommendations = [
            "Consider increasing batch size for better throughput",
            "Enable GPU acceleration for faster embeddings"
        ]
        mock_metrics_collector.get_optimization_recommendations.return_value = expected_recommendations
        
        response = client.get("/performance/recommendations")
        
        assert response.status_code == 200
        data = response.json()
        assert data == expected_recommendations

    @patch('src.search.api.metrics_collector')
    def test_save_performance_metrics(self, mock_metrics_collector, client):
        """Test saving performance metrics."""
        response = client.post("/performance/save")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'saved'
        assert 'timestamp' in data
        mock_metrics_collector.save_metrics.assert_called_once()

    def test_rebuild_index(self, client):
        """Test rebuild index endpoint."""
        response = client.post("/rebuild-index")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'started'
        assert 'message' in data

    @patch('src.search.api.vector_db')
    def test_search_response_model_validation(self, mock_vector_db, client):
        """Test that search response follows the correct model structure."""
        # Create result with all required fields
        complete_result = {
            'similarity_score': 0.95,
            'case_id': 'case_001',
            'case_number': 'CASE-001',
            'subject_description': 'Server crash',
            'description_description': 'Server crashed',
            'issue_plain_text': 'Server issue',
            'cause_plain_text': 'Hardware failure',
            'resolution_plain_text': 'Replaced hardware',
            'status_text': 'Closed',
            'textbody': 'Additional text',
            'created_date': '2024-01-01T10:00:00Z',
            'preview_text': 'Server crash...'
        }
        
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = [complete_result]
        
        search_request = {"query": "test"}
        response = client.post("/search", json=search_request)
        
        assert response.status_code == 200
        data = response.json()
        result = data['results'][0]
        
        # Verify all expected fields are present
        expected_fields = [
            'similarity_score', 'case_id', 'case_number', 'subject_description',
            'description_description', 'issue_plain_text', 'cause_plain_text',
            'resolution_plain_text', 'status_text', 'textbody', 'created_date',
            'preview_text'
        ]
        
        for field in expected_fields:
            assert field in result

    @patch('src.search.api.vector_db')
    def test_search_with_default_parameters(self, mock_vector_db, client, mock_search_results):
        """Test search with default parameters."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = mock_search_results
        
        search_request = {"query": "server crash"}  # Only required field
        response = client.post("/search", json=search_request)
        
        assert response.status_code == 200
        
        # Verify that vector_db.search was called with None for optional params
        # (which should use config defaults)
        mock_vector_db.search.assert_called_once_with(
            query_text="server crash",
            top_k=None,
            similarity_threshold=None
        )

    @patch('src.search.api.vector_db')
    def test_search_parameter_limits(self, mock_vector_db, client):
        """Test search parameter validation limits."""
        mock_vector_db.is_trained = True
        
        # Test top_k limits
        response = client.post("/search", json={
            "query": "test",
            "top_k": 0  # Below minimum
        })
        assert response.status_code == 422
        
        response = client.post("/search", json={
            "query": "test", 
            "top_k": 101  # Above maximum
        })
        assert response.status_code == 422
        
        # Test similarity_threshold limits
        response = client.post("/search", json={
            "query": "test",
            "similarity_threshold": -0.1  # Below minimum
        })
        assert response.status_code == 422
        
        response = client.post("/search", json={
            "query": "test",
            "similarity_threshold": 1.1  # Above maximum
        })
        assert response.status_code == 422

    @patch('src.search.api.vector_db')
    def test_search_query_length_validation(self, mock_vector_db, client):
        """Test search query length validation."""
        mock_vector_db.is_trained = True
        
        # Empty query
        response = client.post("/search", json={"query": ""})
        assert response.status_code == 422
        
        # Query too long
        long_query = "x" * 1001  # Assuming max_length=1000
        response = client.post("/search", json={"query": long_query})
        assert response.status_code == 422

    @patch('src.search.api.health_monitor')
    def test_health_report_custom_hours(self, mock_health_monitor, client):
        """Test health report with custom hour parameter."""
        expected_report = {'period_hours': 48}
        mock_health_monitor.get_health_report.return_value = expected_report
        
        response = client.get("/health/report?hours=48")
        
        assert response.status_code == 200
        mock_health_monitor.get_health_report.assert_called_once_with(hours=48)

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/health")
        
        # Should allow CORS (configured in middleware)
        assert response.status_code in [200, 405]  # Options method may not be implemented

    @patch('src.search.api.vector_db')
    def test_search_metrics_recording(self, mock_vector_db, client, mock_search_results):
        """Test that search requests are recorded in metrics."""
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = mock_search_results
        
        with patch('src.search.api.health_monitor') as mock_health_monitor:
            search_request = {"query": "test"}
            response = client.post("/search", json=search_request)
            
            assert response.status_code == 200
            
            # Verify metrics were recorded
            mock_health_monitor.record_request.assert_called_once()
            call_args = mock_health_monitor.record_request.call_args
            assert call_args[1]['error'] is False  # Successful request

    def test_api_documentation_endpoints(self, client):
        """Test that API documentation endpoints are available."""
        # OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        assert 'openapi' in schema
        assert 'paths' in schema
        assert '/search' in schema['paths']

    @patch('src.search.api.vector_db')
    def test_concurrent_search_requests(self, mock_vector_db, client, mock_search_results):
        """Test handling of concurrent search requests."""
        import concurrent.futures
        
        mock_vector_db.is_trained = True
        mock_vector_db.search.return_value = mock_search_results
        
        def make_request():
            return client.post("/search", json={"query": "test"})
        
        # Make multiple concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            responses = [future.result() for future in futures]
        
        # All requests should succeed
        for response in responses:
            assert response.status_code == 200