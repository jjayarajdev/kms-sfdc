"""Tests for vector database module."""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import json

from src.vectorization.vector_db import VectorDatabase


class TestVectorDatabase:
    """Test cases for VectorDatabase."""
    
    @pytest.fixture
    def sample_case_data(self):
        """Sample case data for testing."""
        return pd.DataFrame({
            'Id': ['500XX0000001', '500XX0000002', '500XX0000003'],
            'CaseNumber': ['00001000', '00001001', '00001002'],
            'Subject': ['Login issue', 'Password reset', 'System error'],
            'Status': ['Open', 'Closed', 'In Progress'],
            'Priority': ['High', 'Medium', 'Low'],
            'CreatedDate': ['2023-01-01', '2023-01-02', '2023-01-03'],
            'combined_text': [
                'User cannot login to system showing error message',
                'User forgot password needs reset functionality',
                'System showing internal server error code 500'
            ]
        })
    
    @pytest.fixture
    def vector_db(self):
        """Create VectorDatabase instance."""
        with patch('src.vectorization.vector_db.config') as mock_config:
            # Mock configuration
            mock_config.vectordb.model_name = "all-MiniLM-L6-v2"
            mock_config.vectordb.batch_size = 2
            mock_config.vectordb.faiss_index_type = "IndexFlatIP"
            mock_config.vectordb.index_path = "test_index.bin"
            mock_config.vectordb.metadata_path = "test_metadata.json"
            
            return VectorDatabase()
    
    @patch('src.vectorization.vector_db.nomic')
    def test_model_loading(self, mock_nomic, vector_db):
        """Test Nomic embedding model loading."""
        mock_embed = Mock()
        mock_nomic.embed.text = mock_embed
        
        vector_db._load_model()
        
        assert vector_db.model == mock_embed
    
    @patch('src.vectorization.vector_db.nomic')
    def test_create_embeddings(self, mock_nomic, vector_db):
        """Test embedding creation with Nomic."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_model.return_value = mock_embeddings
        mock_nomic.embed.text = mock_model
        
        texts = ["test text 1", "test text 2"]
        embeddings = vector_db.create_embeddings(texts)
        
        np.testing.assert_array_equal(embeddings, mock_embeddings)
        mock_model.assert_called_once()
    
    @patch('src.vectorization.vector_db.faiss')
    @patch('src.vectorization.vector_db.nomic')
    def test_build_index(self, mock_nomic, mock_faiss, vector_db, sample_case_data):
        """Test FAISS index building."""
        # Mock nomic
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        mock_model.return_value = mock_embeddings
        mock_nomic.embed.text = mock_model
        
        # Mock FAISS index
        mock_index = Mock()
        mock_faiss.IndexFlatIP.return_value = mock_index
        mock_faiss.normalize_L2 = Mock()
        
        vector_db.build_index(sample_case_data)
        
        # Verify index creation and training
        assert vector_db.is_trained
        assert vector_db.index == mock_index
        mock_index.add.assert_called_once()
        mock_faiss.normalize_L2.assert_called()
        
        # Verify metadata storage
        assert len(vector_db.case_metadata) == 3
        assert vector_db.case_metadata[0]['case_id'] == '500XX0000001'
    
    @patch('src.vectorization.vector_db.faiss')
    @patch('src.vectorization.vector_db.nomic')
    def test_search(self, mock_nomic, mock_faiss, vector_db, sample_case_data):
        """Test similarity search."""
        # Build index first
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        mock_model.return_value = mock_embeddings
        mock_nomic.embed.text = mock_model
        
        mock_index = Mock()
        mock_faiss.IndexFlatIP.return_value = mock_index
        mock_faiss.normalize_L2 = Mock()
        
        vector_db.build_index(sample_case_data)
        
        # Mock search results
        mock_scores = np.array([[0.9, 0.7, 0.5]])
        mock_indices = np.array([[0, 1, 2]])
        mock_index.search.return_value = (mock_scores, mock_indices)
        mock_index.ntotal = 3
        
        # Mock single embedding for query
        mock_model.return_value = np.array([[0.1, 0.2, 0.3]])
        
        results = vector_db.search("login problem", top_k=3, similarity_threshold=0.6)
        
        # Verify results
        assert len(results) == 2  # Only scores >= 0.6
        assert results[0]['similarity_score'] == 0.9
        assert results[0]['case_id'] == '500XX0000001'
        assert results[1]['similarity_score'] == 0.7
    
    def test_search_without_index(self, vector_db):
        """Test search without built index."""
        with pytest.raises(ValueError, match="Index not built"):
            vector_db.search("test query")
    
    @patch('src.vectorization.vector_db.faiss')
    def test_save_load_index(self, mock_faiss, vector_db, sample_case_data):
        """Test saving and loading index."""
        with tempfile.TemporaryDirectory() as temp_dir:
            index_path = Path(temp_dir) / "test_index.bin"
            metadata_path = Path(temp_dir) / "test_metadata.json"
            
            # Mock index for saving
            mock_index = Mock()
            vector_db.index = mock_index
            vector_db.case_metadata = {'0': {'case_id': 'test'}}
            vector_db.is_trained = True
            
            # Test saving
            vector_db.save_index(str(index_path), str(metadata_path))
            
            mock_faiss.write_index.assert_called_once_with(mock_index, str(index_path))
            
            # Verify metadata file was created
            assert metadata_path.exists()
            with open(metadata_path) as f:
                saved_metadata = json.load(f)
            assert saved_metadata == {'0': {'case_id': 'test'}}
            
            # Test loading
            mock_loaded_index = Mock()
            mock_faiss.read_index.return_value = mock_loaded_index
            
            vector_db_new = VectorDatabase()
            vector_db_new.load_index(str(index_path), str(metadata_path))
            
            assert vector_db_new.index == mock_loaded_index
            assert vector_db_new.case_metadata == {'0': {'case_id': 'test'}}
            assert vector_db_new.is_trained
    
    def test_get_stats(self, vector_db):
        """Test getting database statistics."""
        # Test without index
        stats = vector_db.get_stats()
        assert stats['is_trained'] is False
        assert stats['total_vectors'] == 0
        
        # Test with mock index
        mock_index = Mock()
        mock_index.ntotal = 100
        mock_index.d = 384
        vector_db.index = mock_index
        vector_db.is_trained = True
        vector_db.case_metadata = {'0': {}, '1': {}}
        
        stats = vector_db.get_stats()
        assert stats['is_trained'] is True
        assert stats['total_vectors'] == 100
        assert stats['dimension'] == 384
        assert stats['metadata_count'] == 2
    
    @patch('src.vectorization.vector_db.faiss')
    @patch('src.vectorization.vector_db.nomic')
    def test_update_index(self, mock_nomic, mock_faiss, vector_db, sample_case_data):
        """Test updating existing index with new data."""
        # Build initial index
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        mock_model.return_value = mock_embeddings
        mock_nomic.embed.text = mock_model
        
        mock_index = Mock()
        mock_index.ntotal = 3
        mock_faiss.IndexFlatIP.return_value = mock_index
        mock_faiss.normalize_L2 = Mock()
        
        vector_db.build_index(sample_case_data)
        
        # Create new data to add
        new_data = pd.DataFrame({
            'Id': ['500XX0000004'],
            'CaseNumber': ['00001003'],
            'Subject': ['New issue'],
            'combined_text': ['New case description']
        })
        
        # Mock embeddings for new data
        mock_model.return_value = np.array([[0.2, 0.3, 0.4]])
        
        vector_db.update_index(new_data)
        
        # Verify index was updated
        assert len(vector_db.case_metadata) == 4
        assert vector_db.case_metadata[3]['case_id'] == '500XX0000004'