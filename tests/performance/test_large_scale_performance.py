"""
Performance tests for large-scale operations.
"""

import pytest
import pandas as pd
import numpy as np
import time
import tempfile
import os
from unittest.mock import Mock, patch
import threading
import multiprocessing
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

from src.vectorization.vector_db import VectorDatabase
from src.utils.text_processor import TextProcessor
from src.data_extraction.sfdc_client import SFDCClient


@pytest.mark.performance
class TestLargeScalePerformance:
    """Performance tests for large-scale operations."""

    def test_large_dataset_processing_performance(self, mock_config, temp_dir):
        """Test performance with large dataset (10K+ records)."""
        # Create large dataset
        large_dataset_size = 10000
        large_dataset = pd.DataFrame([
            {
                'Id': f'case_{i:06d}',
                'Case_Number': f'CASE-{i:06d}',
                'Subject_Description': f'Performance test case {i} - {self._generate_realistic_subject(i)}',
                'Description_Description': f'Detailed description for performance test case {i}. ' + 
                                         self._generate_realistic_description(i),
                'Issue_Plain_Text': f'Performance issue {i} - {self._generate_realistic_issue(i)}',
                'Resolution_Plain_Text': f'Performance resolution {i} - {self._generate_realistic_resolution(i)}',
                'Status_Text': 'Closed' if i % 3 == 0 else 'Open',
                'CreatedDate': f'2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T10:00:00Z'
            }
            for i in range(large_dataset_size)
        ])
        
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'perf_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'perf_metadata.json')
        mock_config.vectordb.use_gpu = False
        mock_config.vectordb.embedding_batch_size = 100
        mock_config.vectordb.indexing_batch_size = 1000
        
        with patch('src.utils.text_processor.config', mock_config):
            # Test text processing performance
            text_processor = TextProcessor()
            
            start_time = time.time()
            processed_data = text_processor.preprocess_case_data(large_dataset)
            processing_time = time.time() - start_time
            
            # Performance assertions
            assert processing_time < 30.0, f"Text processing took {processing_time:.2f}s, expected < 30s"
            assert len(processed_data) > 0
            
            # Throughput calculation
            throughput = len(processed_data) / processing_time
            assert throughput > 200, f"Processing throughput {throughput:.2f} records/sec, expected > 200"
            
            print(f"Text processing: {processing_time:.2f}s, {throughput:.2f} records/sec")

    def test_vector_database_build_performance(self, mock_config, temp_dir):
        """Test vector database build performance with large dataset."""
        dataset_size = 5000
        
        # Create test dataset
        test_dataset = pd.DataFrame([
            {
                'Id': f'case_{i:05d}',
                'Case_Number': f'CASE-{i:05d}',
                'Subject_Description': f'Vector test case {i}',
                'combined_text': f'Vector performance test case {i} with sufficient content for embedding generation and similarity testing.'
            }
            for i in range(dataset_size)
        ])
        
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'vector_perf_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'vector_perf_metadata.json')
        mock_config.vectordb.use_gpu = False
        mock_config.vectordb.embedding_batch_size = 50
        mock_config.vectordb.indexing_batch_size = 500
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                # Mock embeddings for performance testing
                mock_model = Mock()
                
                def mock_encode_side_effect(texts, **kwargs):
                    # Simulate embedding generation time
                    time.sleep(0.001 * len(texts))  # 1ms per text
                    return np.random.rand(len(texts), 384).astype(np.float32)
                
                mock_model.encode.side_effect = mock_encode_side_effect
                mock_transformer.return_value = mock_model
                
                vector_db = VectorDatabase()
                
                start_time = time.time()
                vector_db.build_index(test_dataset)
                build_time = time.time() - start_time
                
                # Performance assertions
                assert build_time < 60.0, f"Index build took {build_time:.2f}s, expected < 60s"
                assert vector_db.is_trained is True
                assert vector_db.index.ntotal == dataset_size
                
                # Throughput calculation
                throughput = dataset_size / build_time
                assert throughput > 50, f"Build throughput {throughput:.2f} records/sec, expected > 50"
                
                print(f"Vector build: {build_time:.2f}s, {throughput:.2f} records/sec")

    def test_search_performance_large_index(self, mock_config, temp_dir):
        """Test search performance on large index."""
        index_size = 10000
        
        # Create mock vector database with large index
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'search_perf_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'search_perf_metadata.json')
        mock_config.vectordb.use_gpu = False
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
                mock_transformer.return_value = mock_model
                
                vector_db = VectorDatabase()
                
                # Mock large index
                mock_index = Mock()
                mock_index.ntotal = index_size
                mock_index.d = 384
                
                # Mock search results - simulate realistic search times
                def mock_search_side_effect(query_vec, k):
                    # Simulate search time based on index size
                    search_time = 0.001 * np.log(index_size)  # Logarithmic search time
                    time.sleep(search_time)
                    
                    scores = np.random.rand(k) * 0.8 + 0.2  # Scores between 0.2-1.0
                    indices = np.random.choice(index_size, k, replace=False)
                    return scores.reshape(1, -1), indices.reshape(1, -1)
                
                mock_index.search.side_effect = mock_search_side_effect
                vector_db.index = mock_index
                vector_db.is_trained = True
                
                # Create metadata
                vector_db.case_metadata = {
                    i: {
                        'case_id': f'case_{i:05d}',
                        'case_number': f'CASE-{i:05d}',
                        'subject_description': f'Search performance test case {i}',
                        'status_text': 'Closed',
                        'issue_plain_text': f'Issue {i}',
                        'resolution_plain_text': f'Resolution {i}',
                        'created_date': '2024-01-01T10:00:00Z',
                        'combined_text': f'Performance test case {i}...'
                    }
                    for i in range(index_size)
                }
                
                # Test single search performance
                start_time = time.time()
                results = vector_db.search("performance test", top_k=10)
                single_search_time = time.time() - start_time
                
                assert single_search_time < 0.1, f"Single search took {single_search_time:.3f}s, expected < 0.1s"
                assert len(results) == 10
                
                # Test multiple searches performance
                num_searches = 100
                search_times = []
                
                for i in range(num_searches):
                    start = time.time()
                    results = vector_db.search(f"test query {i}", top_k=5)
                    search_time = time.time() - start
                    search_times.append(search_time)
                
                avg_search_time = sum(search_times) / len(search_times)
                max_search_time = max(search_times)
                
                assert avg_search_time < 0.05, f"Average search time {avg_search_time:.3f}s, expected < 0.05s"
                assert max_search_time < 0.2, f"Max search time {max_search_time:.3f}s, expected < 0.2s"
                
                # Search throughput
                searches_per_second = 1.0 / avg_search_time
                assert searches_per_second > 20, f"Search throughput {searches_per_second:.2f} searches/sec, expected > 20"
                
                print(f"Search performance: avg={avg_search_time:.3f}s, max={max_search_time:.3f}s, throughput={searches_per_second:.2f} searches/sec")

    def test_concurrent_search_performance(self, mock_config, temp_dir):
        """Test concurrent search performance."""
        mock_config.vectordb.use_gpu = False
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
                mock_transformer.return_value = mock_model
                
                vector_db = VectorDatabase()
                
                # Mock index for concurrent testing
                mock_index = Mock()
                mock_index.ntotal = 5000
                mock_index.d = 384
                
                def mock_concurrent_search(query_vec, k):
                    # Simulate realistic search time
                    time.sleep(0.01)  # 10ms search time
                    scores = np.random.rand(k) * 0.8 + 0.2
                    indices = np.random.choice(1000, k, replace=False)
                    return scores.reshape(1, -1), indices.reshape(1, -1)
                
                mock_index.search.side_effect = mock_concurrent_search
                vector_db.index = mock_index
                vector_db.is_trained = True
                vector_db.case_metadata = {
                    i: {'case_id': f'case_{i}', 'subject_description': f'Case {i}', 'combined_text': f'Text {i}'}
                    for i in range(1000)
                }
                
                def search_worker(thread_id):
                    """Worker function for concurrent searches."""
                    search_times = []
                    for i in range(10):  # 10 searches per thread
                        start = time.time()
                        results = vector_db.search(f"concurrent test {thread_id}_{i}", top_k=5)
                        search_time = time.time() - start
                        search_times.append(search_time)
                    return search_times
                
                # Test with multiple concurrent threads
                num_threads = 10
                
                start_time = time.time()
                with ThreadPoolExecutor(max_workers=num_threads) as executor:
                    futures = [executor.submit(search_worker, i) for i in range(num_threads)]
                    all_search_times = []
                    for future in futures:
                        all_search_times.extend(future.result())
                
                total_time = time.time() - start_time
                
                # Performance assertions
                avg_search_time = sum(all_search_times) / len(all_search_times)
                total_searches = len(all_search_times)
                
                assert avg_search_time < 0.1, f"Concurrent avg search time {avg_search_time:.3f}s, expected < 0.1s"
                
                # Concurrent throughput should be better than sequential
                concurrent_throughput = total_searches / total_time
                assert concurrent_throughput > 50, f"Concurrent throughput {concurrent_throughput:.2f} searches/sec, expected > 50"
                
                print(f"Concurrent search: {total_searches} searches in {total_time:.2f}s, throughput={concurrent_throughput:.2f} searches/sec")

    def test_memory_usage_large_dataset(self, mock_config, temp_dir):
        """Test memory usage with large datasets."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory_mb = process.memory_info().rss / 1024 / 1024
        
        dataset_size = 20000
        large_dataset = pd.DataFrame([
            {
                'Id': f'case_{i:06d}',
                'combined_text': f'Memory test case {i} ' * 20  # ~300 chars per record
            }
            for i in range(dataset_size)
        ])
        
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'memory_test_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'memory_test_metadata.json')
        mock_config.vectordb.use_gpu = False
        mock_config.vectordb.embedding_batch_size = 100
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                mock_model.encode.return_value = np.random.rand(100, 384).astype(np.float32)  # Batch size
                mock_transformer.return_value = mock_model
                
                vector_db = VectorDatabase()
                vector_db.build_index(large_dataset)
                
                peak_memory_mb = process.memory_info().rss / 1024 / 1024
                memory_increase_mb = peak_memory_mb - initial_memory_mb
                
                # Memory efficiency assertions
                memory_per_record_kb = (memory_increase_mb * 1024) / dataset_size
                assert memory_per_record_kb < 10, f"Memory per record {memory_per_record_kb:.2f}KB, expected < 10KB"
                
                print(f"Memory usage: {memory_increase_mb:.2f}MB increase, {memory_per_record_kb:.2f}KB per record")

    def test_batch_processing_scalability(self, mock_config):
        """Test batch processing scalability."""
        batch_sizes = [10, 50, 100, 500, 1000]
        processing_times = []
        
        for batch_size in batch_sizes:
            # Create test data
            test_data = pd.DataFrame([
                {
                    'Id': f'batch_case_{i}',
                    'Subject_Description': f'Batch test {i}',
                    'combined_text': f'Batch processing test case {i} with content'
                }
                for i in range(batch_size * 5)  # 5 batches of each size
            ])
            
            mock_config.vectordb.embedding_batch_size = batch_size
            
            with patch('src.utils.text_processor.config', mock_config):
                text_processor = TextProcessor()
                
                start_time = time.time()
                processed_data = text_processor.preprocess_case_data(test_data)
                processing_time = time.time() - start_time
                
                processing_times.append(processing_time)
                
                throughput = len(processed_data) / processing_time
                print(f"Batch size {batch_size}: {processing_time:.3f}s, {throughput:.2f} records/sec")
        
        # Verify that larger batch sizes don't significantly degrade performance
        # (within reasonable bounds)
        max_time = max(processing_times)
        min_time = min(processing_times)
        time_ratio = max_time / min_time
        
        assert time_ratio < 3.0, f"Performance degradation ratio {time_ratio:.2f}, expected < 3.0"

    def test_api_load_performance(self, mock_config):
        """Test API performance under load."""
        from fastapi.testclient import TestClient
        from src.search.api import app
        
        client = TestClient(app)
        
        # Mock vector database for load testing
        with patch('src.search.api.vector_db') as mock_vector_db:
            mock_vector_db.is_trained = True
            mock_vector_db.search.return_value = [
                {
                    'similarity_score': 0.8,
                    'case_id': 'load_test_case',
                    'case_number': 'LOAD-001',
                    'subject_description': 'Load test case',
                    'description_description': 'Load testing',
                    'issue_plain_text': 'Load test issue',
                    'cause_plain_text': 'Load test cause',
                    'resolution_plain_text': 'Load test resolution',
                    'status_text': 'Closed',
                    'textbody': 'Load test body',
                    'created_date': '2024-01-01T10:00:00Z',
                    'preview_text': 'Load test preview'
                }
            ]
            
            # Simulate load by making many concurrent requests
            num_requests = 100
            request_times = []
            
            def make_request(request_id):
                start = time.time()
                response = client.post("/search", json={
                    "query": f"load test {request_id}",
                    "top_k": 5
                })
                request_time = time.time() - start
                return response.status_code, request_time
            
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = [executor.submit(make_request, i) for i in range(num_requests)]
                results = [future.result() for future in futures]
            
            total_time = time.time() - start_time
            
            # Verify all requests succeeded
            status_codes = [result[0] for result in results]
            request_times = [result[1] for result in results]
            
            assert all(code == 200 for code in status_codes), "Some requests failed"
            
            # Performance assertions
            avg_response_time = sum(request_times) / len(request_times)
            max_response_time = max(request_times)
            requests_per_second = num_requests / total_time
            
            assert avg_response_time < 0.1, f"Average response time {avg_response_time:.3f}s, expected < 0.1s"
            assert max_response_time < 0.5, f"Max response time {max_response_time:.3f}s, expected < 0.5s"
            assert requests_per_second > 100, f"Request throughput {requests_per_second:.2f} req/sec, expected > 100"
            
            print(f"API load test: {num_requests} requests in {total_time:.2f}s")
            print(f"Avg response: {avg_response_time:.3f}s, Max: {max_response_time:.3f}s")
            print(f"Throughput: {requests_per_second:.2f} req/sec")

    def _generate_realistic_subject(self, i):
        """Generate realistic case subjects for testing."""
        subjects = [
            "server crashes during backup",
            "database connection timeout",
            "network connectivity issues",
            "application performance degradation",
            "memory leak in production",
            "disk space running low",
            "authentication service failure",
            "load balancer configuration error"
        ]
        return subjects[i % len(subjects)]
    
    def _generate_realistic_description(self, i):
        """Generate realistic case descriptions for testing."""
        descriptions = [
            "Production server experiencing unexpected crashes during nightly backup operations. This has been occurring for the past three days and is causing significant business disruption.",
            "Users are reporting timeout errors when attempting to connect to the primary database. Connection attempts fail after 30 seconds with no clear error message.",
            "Intermittent network connectivity problems affecting multiple services in the east coast data center. Packet loss observed between 2-5% during peak hours.",
            "Application response times have increased significantly over the past week. Database queries that normally complete in under 100ms are now taking 2-3 seconds.",
            "Memory usage continues to grow over time in the production application, eventually leading to out-of-memory errors and service restarts.",
            "File system usage has reached 90% capacity on the primary storage array. Need immediate action to prevent service disruption.",
            "Authentication service intermittently failing to validate user credentials, resulting in legitimate users being unable to access the system.",
            "Load balancer health checks are failing due to misconfigured timeout values, causing healthy servers to be marked as unavailable."
        ]
        return descriptions[i % len(descriptions)]
    
    def _generate_realistic_issue(self, i):
        """Generate realistic issue descriptions for testing."""
        issues = [
            "Critical system instability affecting business operations",
            "User access problems impacting productivity",
            "Network infrastructure problems causing service degradation",
            "Performance bottlenecks affecting user experience",
            "Resource exhaustion leading to system failures",
            "Storage capacity issues threatening data availability",
            "Security system malfunctions affecting user authentication",
            "Infrastructure configuration problems affecting service reliability"
        ]
        return issues[i % len(issues)]
    
    def _generate_realistic_resolution(self, i):
        """Generate realistic resolution descriptions for testing."""
        resolutions = [
            "Implemented automated monitoring and adjusted backup scheduling to prevent resource conflicts",
            "Optimized database connection pool settings and increased timeout values to handle peak load",
            "Replaced faulty network hardware and updated routing configuration to eliminate packet loss",
            "Identified and resolved database query inefficiencies, implemented query optimization and indexing improvements",
            "Fixed memory leaks in application code and implemented automated memory monitoring alerts",
            "Provisioned additional storage capacity and implemented automated cleanup policies",
            "Updated authentication service configuration and implemented redundant authentication servers",
            "Corrected load balancer health check configuration and implemented proper monitoring thresholds"
        ]
        return resolutions[i % len(resolutions)]

    @pytest.mark.slow
    def test_end_to_end_performance_benchmark(self, mock_config, temp_dir):
        """Comprehensive end-to-end performance benchmark."""
        print("\n=== KMS-SFDC Performance Benchmark ===")
        
        # Test parameters
        dataset_size = 5000
        search_queries = 50
        
        # Generate comprehensive test dataset
        print(f"Generating {dataset_size} test records...")
        test_dataset = pd.DataFrame([
            {
                'Id': f'bench_{i:05d}',
                'Case_Number': f'BENCH-{i:05d}',
                'Subject_Description': self._generate_realistic_subject(i),
                'Description_Description': self._generate_realistic_description(i),
                'Issue_Plain_Text': self._generate_realistic_issue(i),
                'Resolution_Plain_Text': self._generate_realistic_resolution(i),
                'Status_Text': 'Closed' if i % 3 == 0 else 'Open',
                'CreatedDate': f'2024-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}T10:00:00Z'
            }
            for i in range(dataset_size)
        ])
        
        # Configuration
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'benchmark_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'benchmark_metadata.json')
        mock_config.vectordb.use_gpu = False
        mock_config.vectordb.embedding_batch_size = 100
        mock_config.vectordb.indexing_batch_size = 1000
        
        benchmark_results = {}
        
        # Phase 1: Text Processing
        print("Phase 1: Text Processing Performance")
        with patch('src.utils.text_processor.config', mock_config):
            text_processor = TextProcessor()
            
            start_time = time.time()
            processed_data = text_processor.preprocess_case_data(test_dataset)
            processing_time = time.time() - start_time
            
            processing_throughput = len(processed_data) / processing_time
            benchmark_results['text_processing'] = {
                'time_seconds': processing_time,
                'throughput_records_per_sec': processing_throughput,
                'input_records': len(test_dataset),
                'output_records': len(processed_data)
            }
            
            print(f"  Time: {processing_time:.2f}s")
            print(f"  Throughput: {processing_throughput:.2f} records/sec")
            print(f"  Quality filtering: {len(test_dataset) - len(processed_data)} records filtered")
        
        # Phase 2: Vector Index Building
        print("Phase 2: Vector Index Building Performance")
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                
                def mock_encode_with_timing(texts, **kwargs):
                    # Simulate realistic embedding generation time
                    time.sleep(0.002 * len(texts))  # 2ms per text
                    return np.random.rand(len(texts), 384).astype(np.float32)
                
                mock_model.encode.side_effect = mock_encode_with_timing
                mock_transformer.return_value = mock_model
                
                vector_db = VectorDatabase()
                
                start_time = time.time()
                vector_db.build_index(processed_data)
                build_time = time.time() - start_time
                
                build_throughput = len(processed_data) / build_time
                benchmark_results['index_building'] = {
                    'time_seconds': build_time,
                    'throughput_records_per_sec': build_throughput,
                    'total_vectors': vector_db.index.ntotal
                }
                
                print(f"  Time: {build_time:.2f}s")
                print(f"  Throughput: {build_throughput:.2f} records/sec")
                print(f"  Index size: {vector_db.index.ntotal} vectors")
        
        # Phase 3: Search Performance
        print("Phase 3: Search Performance")
        search_times = []
        search_queries_list = [
            "server crashes during backup",
            "database connection timeout",
            "network connectivity problems",
            "application performance issues",
            "memory leak production",
            "disk space running low",
            "authentication service failure",
            "load balancer configuration"
        ]
        
        for i in range(search_queries):
            query = search_queries_list[i % len(search_queries_list)]
            
            start_time = time.time()
            with patch.object(vector_db, 'create_embeddings') as mock_create_embeddings:
                mock_create_embeddings.return_value = np.random.rand(1, 384).astype(np.float32)
                results = vector_db.search(query, top_k=10)
            search_time = time.time() - start_time
            search_times.append(search_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        max_search_time = max(search_times)
        min_search_time = min(search_times)
        search_throughput = 1.0 / avg_search_time
        
        benchmark_results['search_performance'] = {
            'avg_time_seconds': avg_search_time,
            'min_time_seconds': min_search_time,
            'max_time_seconds': max_search_time,
            'throughput_searches_per_sec': search_throughput,
            'total_searches': search_queries
        }
        
        print(f"  Average search time: {avg_search_time:.3f}s")
        print(f"  Search throughput: {search_throughput:.2f} searches/sec")
        print(f"  Min/Max time: {min_search_time:.3f}s / {max_search_time:.3f}s")
        
        # Performance Summary
        print("\n=== Performance Summary ===")
        total_pipeline_time = (benchmark_results['text_processing']['time_seconds'] + 
                              benchmark_results['index_building']['time_seconds'])
        
        print(f"End-to-end processing: {total_pipeline_time:.2f}s for {dataset_size} records")
        print(f"Overall throughput: {dataset_size / total_pipeline_time:.2f} records/sec")
        print(f"Search latency: {avg_search_time * 1000:.1f}ms average")
        
        # Performance assertions
        assert benchmark_results['text_processing']['throughput_records_per_sec'] > 100
        assert benchmark_results['index_building']['throughput_records_per_sec'] > 50
        assert benchmark_results['search_performance']['avg_time_seconds'] < 0.1
        assert benchmark_results['search_performance']['throughput_searches_per_sec'] > 10
        
        return benchmark_results