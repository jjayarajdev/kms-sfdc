"""
Integration tests for end-to-end search workflow.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import os
from unittest.mock import Mock, patch

from src.vectorization.vector_db import VectorDatabase
from src.utils.text_processor import TextProcessor
from src.data_extraction.sfdc_client import SFDCClient


@pytest.mark.integration
class TestSearchWorkflowIntegration:
    """Integration tests for the complete search workflow."""

    def test_end_to_end_search_workflow(self, mock_config, sample_case_data, temp_dir):
        """Test complete workflow from data processing to search."""
        # Mock configuration paths to use temp directory
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'test_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'test_metadata.json')
        mock_config.vectordb.use_gpu = False  # Disable GPU for testing
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.utils.text_processor.config', mock_config):
                # Step 1: Process text data
                text_processor = TextProcessor()
                processed_data = text_processor.preprocess_case_data(sample_case_data.copy())
                
                assert len(processed_data) > 0
                assert 'combined_text' in processed_data.columns
                
                # Step 2: Build vector database
                with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                    # Mock the transformer to return consistent embeddings
                    mock_model = Mock()
                    mock_embeddings = np.random.rand(len(processed_data), 384).astype(np.float32)
                    mock_model.encode.return_value = mock_embeddings
                    mock_transformer.return_value = mock_model
                    
                    vector_db = VectorDatabase()
                    vector_db.build_index(processed_data)
                    
                    assert vector_db.is_trained is True
                    assert vector_db.index.ntotal == len(processed_data)
                    assert len(vector_db.case_metadata) == len(processed_data)
                
                # Step 3: Perform search
                with patch.object(vector_db, 'create_embeddings') as mock_create_embeddings:
                    mock_create_embeddings.return_value = np.random.rand(1, 384).astype(np.float32)
                    
                    results = vector_db.search("server crash", top_k=5, similarity_threshold=0.1)
                    
                    assert isinstance(results, list)
                    assert len(results) <= 5
                    
                    if len(results) > 0:
                        result = results[0]
                        assert 'similarity_score' in result
                        assert 'case_id' in result
                        assert 'subject_description' in result

    def test_text_processing_integration(self, mock_config):
        """Test text processing with realistic data."""
        # Create test data with various text quality issues
        test_data = pd.DataFrame([
            {
                'Id': 'case_001',
                'Case_Number': 'CASE-001',
                'Subject_Description': 'Server crashes unexpectedly during peak hours',
                'Description_Description': 'The production server experiences sudden crashes without warning, causing significant downtime for our users.',
                'Issue_Plain_Text': 'Server instability and unexpected shutdowns affecting business operations',
                'Resolution_Plain_Text': 'Upgraded server hardware and implemented monitoring system'
            },
            {
                'Id': 'case_002',
                'Case_Number': 'CASE-002',
                'Subject_Description': '<p>Database <b>connection</b> timeout</p>',  # HTML content
                'Description_Description': 'Users reporting timeout when connecting to database. Check https://docs.example.com for details. Contact admin@company.com',  # URLs and emails
                'Issue_Plain_Text': 'Database connectivity problems',
                'Resolution_Plain_Text': 'Optimized connection pool settings'
            },
            {
                'Id': 'case_003',
                'Case_Number': 'CASE-003',
                'Subject_Description': 'Network connectivity problems',
                'Description_Description': 'Intermittent network issues in the east coast data center causing service disruption',
                'Issue_Plain_Text': 'Network instability affecting multiple services',
                'Resolution_Plain_Text': 'Replaced faulty network equipment and updated routing configuration'
            },
            {
                'Id': 'case_004',  # Duplicate content
                'Case_Number': 'CASE-004',
                'Subject_Description': 'Server crashes unexpectedly during peak hours',
                'Description_Description': 'The production server experiences sudden crashes without warning, causing significant downtime for our users.',
                'Issue_Plain_Text': 'Server instability and unexpected shutdowns affecting business operations',
                'Resolution_Plain_Text': 'Upgraded server hardware and implemented monitoring system'
            }
        ])
        
        with patch('src.utils.text_processor.config', mock_config):
            text_processor = TextProcessor()
            processed_data = text_processor.preprocess_case_data(test_data)
            
            # Should have filtered out duplicate
            assert len(processed_data) < len(test_data)
            
            # Should have cleaned HTML, URLs, emails
            for _, row in processed_data.iterrows():
                combined_text = row['combined_text']
                assert '<p>' not in combined_text
                assert '<b>' not in combined_text
                assert 'https://docs.example.com' not in combined_text
                assert 'admin@company.com' not in combined_text
                assert len(combined_text) > 0

    def test_vector_database_persistence(self, mock_config, sample_case_data, temp_dir):
        """Test saving and loading vector database."""
        index_path = os.path.join(temp_dir, 'test_index.bin')
        metadata_path = os.path.join(temp_dir, 'test_metadata.json')
        
        mock_config.vectordb.index_path = index_path
        mock_config.vectordb.metadata_path = metadata_path
        mock_config.vectordb.use_gpu = False
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                # Mock embeddings
                mock_model = Mock()
                mock_embeddings = np.random.rand(len(sample_case_data), 384).astype(np.float32)
                mock_model.encode.return_value = mock_embeddings
                mock_transformer.return_value = mock_model
                
                # Create and train database
                vector_db1 = VectorDatabase()
                vector_db1.build_index(sample_case_data)
                
                original_total = vector_db1.index.ntotal
                original_metadata_count = len(vector_db1.case_metadata)
                
                # Save database
                vector_db1.save_index(create_backup=False)
                
                # Create new instance and load
                vector_db2 = VectorDatabase()
                vector_db2.load_index()
                
                # Verify loaded database
                assert vector_db2.is_trained is True
                assert vector_db2.index.ntotal == original_total
                assert len(vector_db2.case_metadata) == original_metadata_count
                
                # Test search on loaded database
                with patch.object(vector_db2, 'create_embeddings') as mock_create_embeddings:
                    mock_create_embeddings.return_value = mock_embeddings[:1]
                    
                    results = vector_db2.search("test query", top_k=3)
                    assert isinstance(results, list)

    def test_batch_processing_workflow(self, mock_config, temp_dir):
        """Test batch processing of large datasets."""
        # Create larger test dataset
        large_dataset = pd.DataFrame([
            {
                'Id': f'case_{i:04d}',
                'Case_Number': f'CASE-{i:04d}',
                'Subject_Description': f'Test case {i} - Server issue',
                'Description_Description': f'Description for test case {i} describing server problems',
                'Issue_Plain_Text': f'Issue {i} - Server performance degradation',
                'Resolution_Plain_Text': f'Resolution {i} - Applied performance optimizations'
            }
            for i in range(50)  # 50 test cases
        ])
        
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'batch_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'batch_metadata.json')
        mock_config.vectordb.use_gpu = False
        mock_config.vectordb.embedding_batch_size = 10  # Small batch size for testing
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.utils.text_processor.config', mock_config):
                with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                    # Mock embeddings for batch processing
                    mock_model = Mock()
                    
                    def mock_encode_side_effect(texts, **kwargs):
                        return np.random.rand(len(texts), 384).astype(np.float32)
                    
                    mock_model.encode.side_effect = mock_encode_side_effect
                    mock_transformer.return_value = mock_model
                    
                    # Process text
                    text_processor = TextProcessor()
                    processed_data = text_processor.preprocess_case_data(large_dataset)
                    
                    # Build index with batch processing
                    vector_db = VectorDatabase()
                    vector_db.build_index(processed_data)
                    
                    assert vector_db.is_trained is True
                    assert vector_db.index.ntotal == len(processed_data)
                    
                    # Verify batch processing was used (multiple encode calls)
                    assert mock_model.encode.call_count > 1

    def test_error_handling_workflow(self, mock_config, temp_dir):
        """Test error handling throughout the workflow."""
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'error_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'error_metadata.json')
        mock_config.vectordb.use_gpu = False
        
        # Test with invalid data
        invalid_data = pd.DataFrame([
            {
                'Id': None,  # Invalid ID
                'Case_Number': '',
                'Subject_Description': '',
                'Description_Description': '',
                'Issue_Plain_Text': '',
                'Resolution_Plain_Text': ''
            }
        ])
        
        with patch('src.utils.text_processor.config', mock_config):
            text_processor = TextProcessor()
            processed_data = text_processor.preprocess_case_data(invalid_data)
            
            # Should filter out invalid records
            assert len(processed_data) == 0

    def test_incremental_update_workflow(self, mock_config, sample_case_data, temp_dir):
        """Test incremental updates to vector database."""
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'incremental_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'incremental_metadata.json')
        mock_config.vectordb.use_gpu = False
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                
                def mock_encode_side_effect(texts, **kwargs):
                    return np.random.rand(len(texts), 384).astype(np.float32)
                
                mock_model.encode.side_effect = mock_encode_side_effect
                mock_transformer.return_value = mock_model
                
                # Initial index build
                vector_db = VectorDatabase()
                vector_db.build_index(sample_case_data)
                
                initial_total = vector_db.index.ntotal
                
                # Create new data for incremental update
                new_data = pd.DataFrame([
                    {
                        'Id': 'case_new_001',
                        'Case_Number': 'CASE-NEW-001',
                        'Subject_Description': 'New case - Application error',
                        'Description_Description': 'New application error case for testing incremental updates',
                        'Issue_Plain_Text': 'Application throwing unexpected errors',
                        'Resolution_Plain_Text': 'Updated application configuration',
                        'combined_text': 'New case - Application error. New application error case for testing incremental updates. Application throwing unexpected errors. Updated application configuration.'
                    }
                ])
                
                # Perform incremental update
                vector_db.update_index_incremental(new_data)
                
                # Verify update
                assert vector_db.index.ntotal == initial_total + len(new_data)
                assert len(vector_db.case_metadata) == initial_total + len(new_data)

    def test_search_quality_workflow(self, mock_config, temp_dir):
        """Test search quality with known good and bad queries."""
        # Create test data with known relationships
        related_cases = pd.DataFrame([
            {
                'Id': 'case_001',
                'Case_Number': 'CASE-001',
                'Subject_Description': 'Server crashes during backup process',
                'Description_Description': 'Production server crashes every night during automated backup',
                'Issue_Plain_Text': 'Server instability during backup operations',
                'Resolution_Plain_Text': 'Modified backup schedule and increased memory allocation',
                'combined_text': 'Server crashes during backup process. Production server crashes every night during automated backup. Server instability during backup operations. Modified backup schedule and increased memory allocation.'
            },
            {
                'Id': 'case_002',
                'Case_Number': 'CASE-002',
                'Subject_Description': 'Database backup failure',
                'Description_Description': 'Database backup process fails with memory errors',
                'Issue_Plain_Text': 'Backup process encountering memory limitations',
                'Resolution_Plain_Text': 'Increased database server memory and optimized backup queries',
                'combined_text': 'Database backup failure. Database backup process fails with memory errors. Backup process encountering memory limitations. Increased database server memory and optimized backup queries.'
            },
            {
                'Id': 'case_003',
                'Case_Number': 'CASE-003',
                'Subject_Description': 'Network printer offline',
                'Description_Description': 'Office printer not responding to print requests',
                'Issue_Plain_Text': 'Printer connectivity issues in office network',
                'Resolution_Plain_Text': 'Reset printer network settings and updated drivers',
                'combined_text': 'Network printer offline. Office printer not responding to print requests. Printer connectivity issues in office network. Reset printer network settings and updated drivers.'
            }
        ])
        
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'quality_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'quality_metadata.json')
        mock_config.vectordb.use_gpu = False
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                # Create embeddings that simulate semantic similarity
                mock_model = Mock()
                
                # Mock embeddings where backup-related cases are similar
                def mock_encode_side_effect(texts, **kwargs):
                    embeddings = []
                    for text in texts:
                        if 'backup' in text.lower():
                            # Similar embeddings for backup-related content
                            embedding = np.array([0.8] * 384)
                        elif 'server' in text.lower():
                            # Somewhat similar for server-related content
                            embedding = np.array([0.6] * 384)
                        else:
                            # Different embeddings for unrelated content
                            embedding = np.array([0.1] * 384)
                        
                        # Add some noise
                        embedding += np.random.normal(0, 0.1, 384)
                        embeddings.append(embedding)
                    
                    return np.array(embeddings, dtype=np.float32)
                
                mock_model.encode.side_effect = mock_encode_side_effect
                mock_transformer.return_value = mock_model
                
                # Build index
                vector_db = VectorDatabase()
                vector_db.build_index(related_cases)
                
                # Test related query (should find backup cases)
                with patch.object(vector_db, 'create_embeddings') as mock_create_embeddings:
                    # Query about backup issues
                    backup_query_embedding = np.array([[0.8] * 384], dtype=np.float32)
                    mock_create_embeddings.return_value = backup_query_embedding
                    
                    results = vector_db.search("backup process failing", top_k=3, similarity_threshold=0.1)
                    
                    assert len(results) > 0
                    
                    # Should find backup-related cases with higher similarity
                    backup_results = [r for r in results if 'backup' in r['subject_description'].lower()]
                    assert len(backup_results) >= 1

    def test_memory_efficiency_workflow(self, mock_config, temp_dir):
        """Test memory efficiency with larger dataset."""
        # Simulate larger dataset
        large_dataset_size = 100
        
        mock_config.vectordb.index_path = os.path.join(temp_dir, 'memory_index.bin')
        mock_config.vectordb.metadata_path = os.path.join(temp_dir, 'memory_metadata.json')
        mock_config.vectordb.use_gpu = False
        mock_config.vectordb.embedding_batch_size = 20  # Smaller batches to test batching
        
        # Create test data
        large_dataset = pd.DataFrame([
            {
                'Id': f'case_{i:05d}',
                'Case_Number': f'CASE-{i:05d}',
                'Subject_Description': f'Case {i} subject - various issues',
                'Description_Description': f'Detailed description for case {i} with technical details',
                'Issue_Plain_Text': f'Technical issue {i} affecting system performance',
                'Resolution_Plain_Text': f'Applied fix {i} to resolve the reported issue',
                'combined_text': f'Case {i} subject - various issues. Detailed description for case {i} with technical details. Technical issue {i} affecting system performance. Applied fix {i} to resolve the reported issue.'
            }
            for i in range(large_dataset_size)
        ])
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                mock_model = Mock()
                
                # Track memory usage (simplified)
                encode_call_count = 0
                
                def mock_encode_side_effect(texts, **kwargs):
                    nonlocal encode_call_count
                    encode_call_count += 1
                    return np.random.rand(len(texts), 384).astype(np.float32)
                
                mock_model.encode.side_effect = mock_encode_side_effect
                mock_transformer.return_value = mock_model
                
                # Build index
                vector_db = VectorDatabase()
                vector_db.build_index(large_dataset)
                
                # Verify batching occurred
                expected_batches = (large_dataset_size + mock_config.vectordb.embedding_batch_size - 1) // mock_config.vectordb.embedding_batch_size
                assert encode_call_count >= expected_batches
                
                # Verify all data was processed
                assert vector_db.index.ntotal == large_dataset_size
                assert len(vector_db.case_metadata) == large_dataset_size

    def test_configuration_validation_workflow(self, temp_dir):
        """Test workflow with various configuration scenarios."""
        # Test with minimal configuration
        minimal_config = Mock()
        minimal_config.vectordb.model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        minimal_config.vectordb.embedding_dimension = 384
        minimal_config.vectordb.use_gpu = False
        minimal_config.vectordb.index_path = os.path.join(temp_dir, 'minimal_index.bin')
        minimal_config.vectordb.metadata_path = os.path.join(temp_dir, 'minimal_metadata.json')
        minimal_config.vectordb.faiss_index_type = 'IndexFlatIP'
        minimal_config.vectordb.embedding_batch_size = 10
        minimal_config.vectordb.indexing_batch_size = 100
        
        minimal_config.text_processing.min_text_length = 10
        minimal_config.text_processing.max_text_length = 1000
        minimal_config.text_processing.fields_to_vectorize = ['Subject_Description', 'Issue_Plain_Text']
        minimal_config.text_processing.preprocessing.remove_html = True
        minimal_config.text_processing.preprocessing.remove_urls = True
        minimal_config.text_processing.preprocessing.remove_emails = True
        minimal_config.text_processing.preprocessing.lowercase = True
        minimal_config.text_processing.preprocessing.remove_extra_whitespace = True
        
        test_data = pd.DataFrame([
            {
                'Id': 'case_001',
                'Case_Number': 'CASE-001',
                'Subject_Description': 'Test case subject',
                'Issue_Plain_Text': 'Test issue description'
            }
        ])
        
        with patch('src.vectorization.vector_db.config', minimal_config):
            with patch('src.utils.text_processor.config', minimal_config):
                with patch('src.vectorization.vector_db.SentenceTransformer') as mock_transformer:
                    mock_model = Mock()
                    mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
                    mock_transformer.return_value = mock_model
                    
                    # Should work with minimal configuration
                    text_processor = TextProcessor()
                    processed_data = text_processor.preprocess_case_data(test_data)
                    
                    vector_db = VectorDatabase()
                    vector_db.build_index(processed_data)
                    
                    assert vector_db.is_trained is True
                    assert vector_db.index.ntotal == 1