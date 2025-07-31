"""
Unit tests for vector database functionality.
"""

import pytest
import numpy as np
import pandas as pd
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
import json

from src.vectorization.vector_db import VectorDatabase


@pytest.mark.unit
class TestVectorDatabase:
    """Test cases for VectorDatabase class."""

    def test_init(self, mock_config):
        """Test VectorDatabase initialization."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            
            assert vdb.config == mock_config.vectordb
            assert vdb.model is None
            assert vdb.index is None
            assert vdb.case_metadata == {}
            assert vdb.is_trained is False

    def test_get_best_device_cpu_only(self, mock_config):
        """Test device selection when GPU is disabled."""
        mock_config.vectordb.use_gpu = False
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            device = vdb._get_best_device()
            
            assert device == 'cpu'

    @patch('torch.backends.mps.is_available', return_value=True)
    @patch('torch.cuda.is_available', return_value=False)
    def test_get_best_device_mps(self, mock_cuda, mock_mps, mock_config):
        """Test device selection for Apple Silicon GPU."""
        mock_config.vectordb.use_gpu = True
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('torch.backends', Mock()):
                vdb = VectorDatabase()
                device = vdb._get_best_device()
                
                assert device == 'mps'

    @patch('torch.cuda.is_available', return_value=True)
    def test_get_best_device_cuda(self, mock_cuda, mock_config):
        """Test device selection for CUDA GPU."""
        mock_config.vectordb.use_gpu = True
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('torch.backends.mps.is_available', return_value=False):
                vdb = VectorDatabase()
                device = vdb._get_best_device()
                
                assert device == 'cuda'

    @patch('src.vectorization.vector_db.SentenceTransformer')
    def test_load_model(self, mock_transformer, mock_config):
        """Test model loading."""
        mock_model_instance = Mock()
        mock_transformer.return_value = mock_model_instance
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb._load_model()
            
            assert vdb.model == mock_model_instance
            mock_transformer.assert_called_once_with(
                mock_config.vectordb.model_name, 
                device='cpu'
            )

    @patch('src.vectorization.vector_db.SentenceTransformer')
    def test_create_embeddings(self, mock_transformer, mock_config, sample_embeddings):
        """Test embedding creation."""
        mock_model = Mock()
        mock_model.encode.return_value = sample_embeddings[:1]  # Single embedding
        mock_transformer.return_value = mock_model
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            embeddings = vdb.create_embeddings(['test text'])
            
            assert embeddings.shape == (1, 384)
            mock_model.encode.assert_called_once()

    def test_get_stats_untrained(self, mock_config):
        """Test getting stats for untrained database."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            stats = vdb.get_stats()
            
            expected = {
                'is_trained': False,
                'total_vectors': 0,
                'dimension': 0,
                'index_type': 'IndexIVFPQ',
                'model_name': mock_config.vectordb.model_name,
                'metadata_count': 0
            }
            assert stats == expected

    @patch('faiss.IndexFlatIP')
    def test_get_stats_trained(self, mock_index_class, mock_config):
        """Test getting stats for trained database."""
        mock_index = Mock()
        mock_index.ntotal = 100
        mock_index.d = 384
        mock_index_class.return_value = mock_index
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb.index = mock_index
            vdb.is_trained = True
            vdb.case_metadata = {i: {} for i in range(100)}
            
            stats = vdb.get_stats()
            
            assert stats['is_trained'] is True
            assert stats['total_vectors'] == 100
            assert stats['dimension'] == 384
            assert stats['metadata_count'] == 100

    def test_search_not_trained(self, mock_config):
        """Test search when database is not trained."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            
            with pytest.raises(ValueError, match="Index not built"):
                vdb.search("test query")

    @patch('faiss.normalize_L2')
    @patch('src.vectorization.vector_db.SentenceTransformer')
    def test_search_success(self, mock_transformer, mock_normalize, mock_config, 
                          mock_faiss_index, sample_case_data):
        """Test successful search operation."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1] * 384])
        mock_transformer.return_value = mock_model
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb.index = mock_faiss_index
            vdb.is_trained = True
            vdb.case_metadata = {
                0: {
                    'case_id': 'case_001',
                    'case_number': 'CASE-001',
                    'subject_description': 'Server crashes',
                    'status_text': 'Closed',
                    'issue_plain_text': 'Server issues',
                    'resolution_plain_text': 'Fixed server',
                    'created_date': '2024-01-01',
                    'combined_text': 'Server crashes...'
                }
            }
            
            results = vdb.search("server crash", top_k=5, similarity_threshold=0.7)
            
            assert len(results) == 1
            assert results[0]['similarity_score'] == 0.95
            assert results[0]['case_id'] == 'case_001'
            assert 'subject_description' in results[0]

    def test_search_no_results_threshold(self, mock_config, mock_faiss_index):
        """Test search with high similarity threshold returning no results."""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[0.1] * 384])
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer', return_value=mock_model):
                vdb = VectorDatabase()
                vdb.index = mock_faiss_index
                vdb.is_trained = True
                vdb.case_metadata = {0: {'case_id': 'test'}}
                
                # Mock search to return low similarity scores
                vdb.index.search.return_value = (
                    np.array([[0.3, 0.2, 0.1]]),  # Low scores
                    np.array([[0, 1, 2]])
                )
                
                results = vdb.search("test", similarity_threshold=0.8)  # High threshold
                
                assert len(results) == 0

    @patch('faiss.write_index')
    def test_save_index(self, mock_write, mock_config, temp_dir):
        """Test saving index to disk."""
        mock_index = Mock()
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb.index = mock_index
            vdb.is_trained = True
            vdb.case_metadata = {'0': {'case_id': 'test'}}
            
            index_path = os.path.join(temp_dir, 'test_index.bin')
            metadata_path = os.path.join(temp_dir, 'test_metadata.json')
            
            vdb.save_index(index_path, metadata_path, create_backup=False)
            
            mock_write.assert_called_once_with(mock_index, index_path)
            assert os.path.exists(metadata_path)

    def test_save_index_not_trained(self, mock_config):
        """Test saving index when not trained raises error."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            
            with pytest.raises(ValueError, match="No index to save"):
                vdb.save_index()

    @patch('faiss.read_index')
    def test_load_index(self, mock_read, mock_config, temp_dir):
        """Test loading index from disk."""
        # Create test metadata file
        metadata_path = os.path.join(temp_dir, 'test_metadata.json')
        test_metadata = {'0': {'case_id': 'test_case'}}
        with open(metadata_path, 'w') as f:
            json.dump(test_metadata, f)
        
        # Create test index file
        index_path = os.path.join(temp_dir, 'test_index.bin')
        with open(index_path, 'w') as f:
            f.write("mock index")
        
        mock_index = Mock()
        mock_read.return_value = mock_index
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer'):
                vdb = VectorDatabase()
                vdb.load_index(index_path, metadata_path)
                
                assert vdb.index == mock_index
                assert vdb.is_trained is True
                assert vdb.case_metadata == {0: {'case_id': 'test_case'}}

    def test_load_index_file_not_found(self, mock_config):
        """Test loading index with missing files."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            
            with pytest.raises(FileNotFoundError):
                vdb.load_index('nonexistent.bin', 'nonexistent.json')

    @patch('faiss.IndexFlatIP')
    def test_create_production_index_flat(self, mock_index_class, mock_config):
        """Test creating flat index for small datasets."""
        mock_index = Mock()
        mock_index_class.return_value = mock_index
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            index = vdb._create_production_index(384, 1000)  # Small dataset
            
            assert index == mock_index
            mock_index_class.assert_called_once_with(384)

    @patch('faiss.IndexHNSWFlat')
    def test_create_production_index_hnsw(self, mock_index_class, mock_config):
        """Test creating HNSW index for medium datasets."""
        mock_index = Mock()
        mock_index.hnsw = Mock()
        mock_index_class.return_value = mock_index
        
        mock_config.vectordb.faiss_index_type = "IndexHNSWFlat"
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            index = vdb._create_production_index(384, 75000)  # Medium dataset
            
            assert index == mock_index
            mock_index_class.assert_called_once_with(384, 32)

    def test_get_scale_category(self, mock_config):
        """Test dataset scale categorization."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            
            assert vdb._get_scale_category(50000) == 'small'
            assert vdb._get_scale_category(500000) == 'medium'
            assert vdb._get_scale_category(2000000) == 'large'
            assert vdb._get_scale_category(6000000) == 'extra_large'

    def test_get_optimization_recommendations(self, mock_config):
        """Test optimization recommendations."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb.case_metadata = {i: {} for i in range(100)}
            
            recommendations = vdb._get_optimization_recommendations(3000000, 'IndexFlatIP')
            
            assert any('IndexIVFPQ' in rec for rec in recommendations)
            assert any('GPU acceleration' in rec for rec in recommendations)

    @patch('src.vectorization.vector_db.SentenceTransformer')
    @patch('faiss.IndexFlatIP')
    @patch('faiss.normalize_L2')
    def test_build_index(self, mock_normalize, mock_index_class, mock_transformer, 
                        mock_config, sample_case_data, sample_embeddings):
        """Test building index from case data."""
        # Setup mocks
        mock_model = Mock()
        mock_model.encode.return_value = sample_embeddings
        mock_transformer.return_value = mock_model
        
        mock_index = Mock()
        mock_index.ntotal = len(sample_case_data)
        mock_index_class.return_value = mock_index
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb.build_index(sample_case_data)
            
            assert vdb.is_trained is True
            assert vdb.index == mock_index
            assert len(vdb.case_metadata) == len(sample_case_data)
            
            # Check metadata structure
            assert 'case_id' in vdb.case_metadata[0]
            assert 'subject_description' in vdb.case_metadata[0]

    def test_get_index_health_metrics_not_trained(self, mock_config):
        """Test health metrics for untrained index."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            metrics = vdb.get_index_health_metrics()
            
            assert metrics['status'] == 'not_trained'
            assert metrics['health'] == 'unhealthy'

    @patch('faiss.IndexFlatIP')
    def test_get_index_health_metrics_healthy(self, mock_index_class, mock_config):
        """Test health metrics for healthy index."""
        mock_index = Mock()
        mock_index.ntotal = 1000
        mock_index.d = 384
        mock_index_class.return_value = mock_index
        
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb.index = mock_index
            vdb.is_trained = True
            vdb.case_metadata = {i: {} for i in range(1000)}
            
            metrics = vdb.get_index_health_metrics()
            
            assert metrics['status'] == 'healthy'
            assert metrics['total_vectors'] == 1000
            assert metrics['dimension'] == 384
            assert metrics['scale_category'] == 'small'
            assert isinstance(metrics['recommended_actions'], list)

    @patch('src.vectorization.vector_db.time.time')
    def test_create_embeddings_large_scale_batching(self, mock_time, mock_config):
        """Test large-scale embedding creation with batching."""
        mock_time.side_effect = [0, 0.1, 0.2]  # Mock time progression
        
        mock_model = Mock()
        mock_model.encode.return_value = np.random.rand(5, 384).astype(np.float32)
        
        with patch('src.vectorization.vector_db.config', mock_config):
            with patch('src.vectorization.vector_db.SentenceTransformer', return_value=mock_model):
                vdb = VectorDatabase()
                texts = [f'text_{i}' for i in range(5)]
                
                embeddings = vdb._create_embeddings_large_scale(texts)
                
                assert embeddings.shape == (5, 384)
                mock_model.encode.assert_called()

    def test_store_metadata_batch(self, mock_config, sample_case_data):
        """Test batch metadata storage."""
        with patch('src.vectorization.vector_db.config', mock_config):
            vdb = VectorDatabase()
            vdb._store_metadata_batch(sample_case_data)
            
            assert len(vdb.case_metadata) == len(sample_case_data)
            
            # Check first record metadata
            metadata = vdb.case_metadata[0]
            assert metadata['case_id'] == 'case_001'
            assert metadata['case_number'] == 'CASE-001'
            assert metadata['subject_description'] == 'Server crashes unexpectedly'
            assert 'combined_text' in metadata