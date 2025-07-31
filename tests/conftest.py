"""
Pytest configuration and fixtures for KMS-SFDC tests.
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock
import json

from src.utils.config import Config
from src.vectorization.vector_db import VectorDatabase
from src.data_extraction.sfdc_client import SFDCClient
from src.utils.text_processor import TextProcessor
from src.utils.health_monitor import HealthMonitor
from src.utils.backup_manager import BackupManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config(temp_dir):
    """Create a mock configuration for testing."""
    config_data = {
        'vectordb': {
            'model_name': 'sentence-transformers/all-MiniLM-L6-v2',
            'embedding_dimension': 384,
            'use_gpu': False,
            'index_path': os.path.join(temp_dir, 'test_index.bin'),
            'metadata_path': os.path.join(temp_dir, 'test_metadata.json'),
            'embedding_batch_size': 10,
            'indexing_batch_size': 100,
            'faiss_index_type': 'IndexFlatIP'
        },
        'search': {
            'default_top_k': 10,
            'similarity_threshold': 0.4,
            'max_results': 50
        },
        'text_processing': {
            'min_text_length': 10,
            'max_text_length': 10000,
            'fields_to_vectorize': [
                'Case_Number',
                'Subject_Description',
                'Description_Description',
                'Issue_Plain_Text',
                'Resolution_Plain_Text',
                'Status_Text'
            ]
        },
        'salesforce': {
            'username': 'test@example.com',
            'password': 'testpass',
            'security_token': 'testtoken',
            'login_url': 'https://test.salesforce.com',
            'api_version': '58.0',
            'query_batch_size': 200
        }
    }
    
    config = Mock(spec=Config)
    for key, value in config_data.items():
        if isinstance(value, dict):
            mock_section = Mock()
            for sub_key, sub_value in value.items():
                setattr(mock_section, sub_key, sub_value)
            setattr(config, key, mock_section)
        else:
            setattr(config, key, value)
    
    return config


@pytest.fixture
def sample_case_data():
    """Create sample case data for testing."""
    return pd.DataFrame([
        {
            'Id': 'case_001',
            'Case_Number': 'CASE-001',
            'Subject_Description': 'Server crashes unexpectedly',
            'Description_Description': 'The server crashes without warning during peak hours',
            'Issue_Plain_Text': 'Unexpected server crashes causing downtime',
            'Resolution_Plain_Text': 'Increased memory allocation and monitoring',
            'Status_Text': 'Closed',
            'CreatedDate': '2024-01-01T10:00:00Z',
            'combined_text': 'Server crashes unexpectedly. The server crashes without warning during peak hours. Unexpected server crashes causing downtime. Increased memory allocation and monitoring.'
        },
        {
            'Id': 'case_002',
            'Case_Number': 'CASE-002',
            'Subject_Description': 'Database connection timeout',
            'Description_Description': 'Application cannot connect to database after timeout',
            'Issue_Plain_Text': 'Database connection issues affecting user access',
            'Resolution_Plain_Text': 'Updated connection pool settings',
            'Status_Text': 'Resolved',
            'CreatedDate': '2024-01-02T14:30:00Z',
            'combined_text': 'Database connection timeout. Application cannot connect to database after timeout. Database connection issues affecting user access. Updated connection pool settings.'
        },
        {
            'Id': 'case_003',
            'Case_Number': 'CASE-003',
            'Subject_Description': 'Network connectivity problems',
            'Description_Description': 'Intermittent network issues causing service disruption',
            'Issue_Plain_Text': 'Network connectivity problems in east coast region',
            'Resolution_Plain_Text': 'Replaced faulty network switches',
            'Status_Text': 'Closed',
            'CreatedDate': '2024-01-03T09:15:00Z',
            'combined_text': 'Network connectivity problems. Intermittent network issues causing service disruption. Network connectivity problems in east coast region. Replaced faulty network switches.'
        }
    ])


@pytest.fixture
def sample_embeddings():
    """Create sample embeddings for testing."""
    np.random.seed(42)
    return np.random.rand(3, 384).astype(np.float32)


@pytest.fixture
def mock_sfdc_client():
    """Create a mock SFDC client."""
    mock_client = Mock(spec=SFDCClient)
    mock_client.extract_case_data.return_value = pd.DataFrame([
        {
            'Id': 'test_case_001',
            'Case_Number__c': 'TEST-001',
            'Subject_Description__c': 'Test case subject',
            'Description_Description__c': 'Test case description',
            'Status_Text__c': 'Open',
            'CreatedDate': '2024-01-01T10:00:00Z'
        }
    ])
    mock_client.test_connection.return_value = True
    return mock_client


@pytest.fixture
def mock_vector_db(mock_config, temp_dir):
    """Create a mock vector database."""
    mock_db = Mock(spec=VectorDatabase)
    mock_db.config = mock_config.vectordb
    mock_db.is_trained = True
    mock_db.index = Mock()
    mock_db.index.ntotal = 3
    mock_db.case_metadata = {
        0: {'case_id': 'case_001', 'subject_description': 'Test case 1'},
        1: {'case_id': 'case_002', 'subject_description': 'Test case 2'},
        2: {'case_id': 'case_003', 'subject_description': 'Test case 3'}
    }
    return mock_db


@pytest.fixture
def mock_search_results():
    """Create mock search results."""
    return [
        {
            'similarity_score': 0.95,
            'case_id': 'case_001',
            'case_number': 'CASE-001',
            'subject_description': 'Server crashes unexpectedly',
            'status_text': 'Closed',
            'issue_plain_text': 'Unexpected server crashes',
            'resolution_plain_text': 'Increased memory allocation',
            'created_date': '2024-01-01T10:00:00Z',
            'preview_text': 'Server crashes unexpectedly...'
        },
        {
            'similarity_score': 0.75,
            'case_id': 'case_002',
            'case_number': 'CASE-002',
            'subject_description': 'Database connection timeout',
            'status_text': 'Resolved',
            'issue_plain_text': 'Database connection issues',
            'resolution_plain_text': 'Updated connection pool',
            'created_date': '2024-01-02T14:30:00Z',
            'preview_text': 'Database connection timeout...'
        }
    ]


@pytest.fixture
def sample_health_metrics():
    """Create sample health metrics."""
    return {
        'timestamp': '2024-01-01T10:00:00Z',
        'cpu_usage': 45.2,
        'memory_usage': 62.8,
        'disk_usage': 78.5,
        'active_connections': 15,
        'avg_response_time': 120.5,
        'error_rate': 0.02,
        'total_requests': 1500,
        'successful_requests': 1470,
        'failed_requests': 30
    }


@pytest.fixture
def sample_performance_metrics():
    """Create sample performance metrics."""
    return {
        'operation_stats': {
            'vector_search': {
                'total_calls': 100,
                'avg_time_ms': 45.2,
                'min_time_ms': 12.5,
                'max_time_ms': 180.3,
                'success_rate': 0.98
            },
            'embedding_creation': {
                'total_calls': 50,
                'avg_time_ms': 120.8,
                'min_time_ms': 85.2,
                'max_time_ms': 250.1,
                'success_rate': 1.0
            }
        },
        'batch_processing': {
            'total_batches': 20,
            'avg_batch_size': 25,
            'avg_processing_time_ms': 2500.5,
            'throughput_records_per_sec': 10.2
        }
    }


@pytest.fixture
def mock_sentence_transformer():
    """Create a mock sentence transformer model."""
    mock_model = Mock()
    mock_model.encode.return_value = np.random.rand(1, 384).astype(np.float32)
    return mock_model


@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index."""
    mock_index = Mock()
    mock_index.ntotal = 3
    mock_index.d = 384
    mock_index.is_trained = True
    mock_index.search.return_value = (
        np.array([[0.95, 0.75, 0.65]]),  # scores
        np.array([[0, 1, 2]])  # indices
    )
    return mock_index


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, temp_dir):
    """Setup test environment with proper paths."""
    # Set test environment variables
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setenv("TEST_DATA_DIR", temp_dir)
    
    # Create test directories
    os.makedirs(os.path.join(temp_dir, "data"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "logs"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "backups"), exist_ok=True)


@pytest.fixture
def api_client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from src.search.api import app
    return TestClient(app)


class MockSFDCResponse:
    """Mock SFDC API response."""
    def __init__(self, records):
        self.records = records
        self.done = True
        self.totalSize = len(records)


@pytest.fixture
def mock_sfdc_response():
    """Create mock SFDC response data."""
    return MockSFDCResponse([
        {
            'Id': 'test_001',
            'Case_Number__c': 'TEST-001',
            'Subject_Description__c': 'Test subject',
            'Description_Description__c': 'Test description',
            'Issue_Plain_Text__c': 'Test issue',
            'Resolution_Plain_Text__c': 'Test resolution',
            'Status_Text__c': 'Open',
            'CreatedDate': '2024-01-01T10:00:00.000+0000'
        }
    ])